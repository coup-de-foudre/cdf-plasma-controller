# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Operating posture

This software ships to physical Raspberry Pis driving plasma-tube PWM hardware in the field. Default to **minimal, surgical changes**. The author rarely has hardware accessible for testing, so:

- Prefer behavior-preserving refactors over redesigns.
- Treat `osc_runner.py` + `config/irobot.conf` + `deploy/plasma_controller.service` as the deployed contract — Pis are identified by CPU serial and select their config section from `irobot.conf`.
- Do not introduce frequency slewing, soft-start ramps, or other "safety" behaviors unless explicitly asked. None currently exist (see "Hardware control flow" below); silently adding one would change real-world output.

## Commands

Dependencies are pinned in `requirements.txt` (which includes `-e ./vendor/python-osc` for the vendored OSC library). `tox.ini` defines test/lint envs; `Makefile` wraps Docker-based testing.

```bash
pip3 install -r requirements.txt        # install runtime + test deps
pytest                                   # run tests
pytest tests/modulator/test_callback_modulator.py::TestName::test_x
tox                                      # full matrix (py34/py35/py36 + flake8)
tox -e py36-flake8                       # lint only (plasma/ + tests/)
./plasma_controller.py -f 10000          # CLI entry point (keyboard mode)
./osc_runner.py -vvv                     # production entry point; reads config/irobot.conf
make test                                # builds Docker image and runs `tox` inside it
```

`tox.ini` declares envs for Python 3.4/3.5/3.6 — historical, matching the Pi OS at the time the project was written. Modern Pi OS images ship newer Python; the vendored `python-osc` 1.6.7 uses `from collections import Iterable`, which breaks on Python ≥ 3.10, so verify the target Pi's Python version before assuming a clean install.

A separate uv-based packaging effort lives on its own branch/PR — `master` intentionally stays on the original `requirements.txt` + `tox` toolchain to minimize risk to deployed Pis.

## Two entry points, two configurations

- **`plasma_controller.py`** — interactive/CLI. All parameters via argparse flags. Used for tuning a tube (keyboard controller) or ad-hoc OSC runs.
- **`osc_runner.py`** — production. Reads `/proc/cpuinfo` for the Pi's serial number, looks up the matching `[serial]` section in `config/irobot.conf`, and constructs an `OSCController` with `immediate_on=True`. This is what the systemd unit (`deploy/plasma_controller.service`) executes.

Adding a new Pi to the fleet means adding a new `[<serial>]` section to `irobot.conf`. The `[MOCK]` section is the fallback when no serial is detected (e.g., running on a dev laptop).

## Hardware control flow

The signal chain, top to bottom:

```
OSC msg / keyboard ──▶ Controller ──▶ {Modulator, Interrupter} ──▶ PWM ──▶ pigpiod ──▶ GPIO
```

- **`PiHardwarePWM`** (`plasma/pwm/pi_pwm.py`) — wraps `pigpio.pi().hardware_PWM(pin, freq, duty_ticks)`. `start()` writes the configured frequency; `stop()` writes frequency=0. Both are instantaneous; there is no ramp.
- **`SimpleInterrupter`** (`plasma/interrupter/simple_interrupter.py`) — a chopper. A `ThreadPoolExecutor` worker loops calling `pwm.start()`/`pwm.stop()` at a low frequency (default 100 Hz) and duty cycle. With `duty_cycle == 1.0` (the production default) the stop branch is never taken, so the loop runs but never gates the PWM. Setting `duty_cycle < 1.0` enables actual interruption.
- **`CallbackModulator`** (`plasma/modulator/callback_modulator.py`) — FM modulation. Worker thread invokes a callback with `center + spread·sin(2π·f·t)`, with phase carry across frequency changes to avoid discontinuities. Production sets `frequency=0.0` (idle); the modulator is plumbed but not used to control intensity. **The author has noted that running the FM modulator stresses the driver hardware and burns it out — leave it idle unless explicitly enabling it.**
- **Pin numbering** is BCM (pigpio convention). `--pin` is restricted to {12, 13, 18, 19} — the Pi's four hardware-PWM-capable BCM pins. `pin=18` in `irobot.conf` = BCM 18 = physical header pin 12.

### Teardown ordering (load-bearing)

Both `OSCController.shutdown` / `set_pwm_off` and `KeyboardController.__exit__` stop in this order: **modulator → interrupter → PWM**. Reversing this order can leave the modulator writing frequencies after the PWM has been stopped, or the interrupter calling start on a torn-down PWM. Preserve the order if touching these paths.

### Startup behavior

- `OSCController(immediate_on=True)` (used by `osc_runner.py`): `start()` energizes the PWM at the configured center frequency immediately when the process starts. No ramp.
- `OSCController(immediate_on=False)` (used by `plasma_controller.py --controller-type OSC`): the OSC server starts but the PWM stays off until a `/<root>/start` message arrives.
- `KeyboardController.__enter__`: starts PWM, interrupter, and modulator together.

## OSC surface

`OSCController._get_dispatcher` (`plasma/controller/osc_controller.py:347`) is the authoritative list of OSC routes. Routes are parameterized by `address_roots` (e.g., `pwm`, `pwm1`, …); `osc_runner.py` reads roots from the config's `osc_roots` field (comma-separated). Default UDP port is 5005. The server is `pythonosc.osc_server.ThreadingOSCUDPServer` — UDP only.

The "fine control" knobs (`/<root>/fine/spread`, `/<root>/fine/value`) implement small modulations around the center frequency: `actual_freq = center + spread·value` with `value ∈ [-1, 1]`. This is the intended mechanism for live performance control (vs. the FM modulator).

### What live performance actually uses

There are **two** ways to drive the live show, and they share the same OSC endpoints:

1. **IAnnix over LAN** (historical / legacy fallback): `extras/iannix/P-Tubes_w-SC_MM_G-2.iannix` running on a laptop, broadcasting `osc://192.168.1.255:5005/<root>/fine/value <float>` to every Pi.
2. **Local score player** (`score_player.py` + `deploy/plasma_player.service`): each Pi runs its own player process that reads `scores/<root>.csv`, samples it at 50 Hz, and sends OSC to **localhost:5005**. A hardware switch on a GPIO pin (default BCM 4) starts/pauses playback; long-press kills it. See `scores/README.md` for the score format.

Both paths use only `/<root>/fine/value`, `/<root>/start`, and `/<root>/stop`. Neither touches `/center-frequency`, `/duty-cycle`, `/fm/*`, or `/interrupter/*` during a performance. Center frequency, spread, and duty cycle come from `irobot.conf` and are set once at startup. **If a change appears to break "fine value" handling or the start/stop transitions, it will break the live show.**

The two sources can technically coexist (the OSC server listens on `0.0.0.0:5005`, so it accepts both LAN broadcasts and localhost messages), but in practice run only one at a time.

### Score player

- Entry point: `score_player.py` (root). Reads `irobot.conf` to determine the OSC root and `button_pin` for this Pi.
- State machine (`plasma/player/state_machine.py`): pure logic, IDLE/PLAYING/PAUSED. **Always boots in IDLE** even if the switch is closed at power-up — this is intentional and addresses the "stuck-on switch at boot" failure mode.
- Long-press kill: when the 1 s threshold timer expires *while the button is still held*, the player immediately sends three `/<root>/stop` messages (50 ms apart) and resets to IDLE. The trailing rising edge is consumed silently. This gives the user immediate feedback that their hold registered. Modifying this timing changes the "feel" of the kill — leave it alone unless asked.
- Localhost OSC client: `plasma/player/osc_client.py`. The player is a strict layer on top of the existing controller — `OSCController` is unchanged.
- Mock mode for laptop testing: `--mock-button` reads stdin (`<Enter>` = short press, `h<Enter>` = long press, `q<Enter>` = quit). See "Local end-to-end smoke test" below.

### Local end-to-end smoke test (no Pi required)

```bash
# Terminal 1 — mock controller
./plasma_controller.py --mock --controller-type OSC -f 30000 -vvv

# Terminal 2 — player against localhost
./score_player.py --mock-button --root pwm1 --score scores/pwm1.csv -vvv
```

Press `<Enter>` in terminal 2 → terminal 1 logs `/pwm1/start` then a stream of `/pwm1/fine/value <n>` messages. `<Enter>` again → `/pwm1/stop`. `h<Enter>` → triple `/pwm1/stop` and the player returns to IDLE.

## Tests

Tests cover only `CallbackModulator` (`tests/modulator/test_callback_modulator.py`). The PWM, interrupter, and controllers have no unit tests — they're tested on hardware. Don't assume regressions will be caught by CI.

## Files worth knowing about

- `config/irobot.conf` — per-Pi tube tuning (center frequency, spread, duty cycle). The comments in this file are the authoritative record of which Pi drives which physical tube.
- `deploy/plasma_controller.service` — systemd unit. `ExecStart=/home/pi/cdf-plasma-controller/osc_runner.py -vvv` relies on the script's `#!/usr/bin/env python3` shebang and on `requirements.txt` deps being installed into the Pi's system Python (`sudo pip3 install -r requirements.txt`).
- `deploy/startup.sh` — historical SSH fan-out script for starting controllers across the fleet from a workstation. Most lines are commented; kept as reference.
- `vendor/python-osc` — vendored copy of python-osc 1.6.7 (git subtree, no local modifications). Installed editable via `-e ./vendor/python-osc` in `requirements.txt`. `osc_runner.py` also adds `vendor/*` to `sys.path` at import time as a belt-and-suspenders fallback.
- `pigpio/` — vendored pigpio C source for installing the daemon on the Pi (`make pigpio`).
