#!/usr/bin/env python3
#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
# This file is part of the CdF Plasma Controller. See the top-level COPYING
# file for the AGPLv3 license terms.
#
"""Stand-alone score player.

Hardware switch on a GPIO input drives playback of a locally-stored score
that talks OSC to the existing plasma controller process on localhost. This
replaces the network-broadcast IAnnix flow for shows that don't need the
laptop in the loop.

Usage on a Pi:
    ./score_player.py -vvv

Usage on a laptop (no GPIO needed):
    # Terminal 1 — the controller
    ./plasma_controller.py --mock --controller-type OSC -f 30000 -vvv
    # Terminal 2 — the player
    ./score_player.py --mock-button --root pwm1 --score scores/pwm1.csv -vvv
"""
import argparse
import glob
import logging
import os
import signal
import sys
import threading
import time
from configparser import ConfigParser

# Match the dependency-resolution hack in osc_runner.py so this script runs
# the same way (executable script, no install step) on the deployed Pis.
_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
if _BASE_PATH not in sys.path:
    sys.path += [_BASE_PATH]
for _vendor_path in glob.glob(os.path.join(_BASE_PATH, 'vendor', '*')):
    if _vendor_path not in sys.path:
        sys.path += [_vendor_path]

from plasma.player.osc_client import PlayerOSCClient
from plasma.player.score import Score
from plasma.player.state_machine import (
    Action, ActionKind, PlayerStateMachine, State)
from plasma.utils.runtime import cpu_serial, parse_bind_host, set_up_logging


_DEFAULT_CONFIG = os.path.join(_BASE_PATH, 'config', 'irobot.conf')
_DEFAULT_SCORES_DIR = os.path.join(_BASE_PATH, 'scores')
_TICK_HZ = 50.0


def _logger():
    return logging.getLogger(__name__)


def _resolve_from_config(config_file: str):
    """Read irobot.conf, look up the section matching this Pi's CPU serial,
    and return (root, button_pin). Falls back to MOCK if no serial."""
    config = ConfigParser()
    with open(config_file, 'r') as fp:
        config.read_file(fp)
    serial = cpu_serial()
    if serial is None or not config.has_section(serial):
        section = "MOCK"
        _logger().warning(
            "No matching config section for serial=%s; using %s",
            serial, section)
    else:
        section = serial
    osc_roots = config.get(section, "osc_roots")
    root = osc_roots.split(',')[0].strip()
    # button_pin is optional; fall back to a sane default.
    if config.has_option(section, "button_pin"):
        button_pin = config.getint(section, "button_pin")
    else:
        button_pin = 4
        _logger().info(
            "No button_pin set for section %s; defaulting to BCM %d",
            section, button_pin)
    return root, button_pin


class Player:
    """Wires the state machine, score, OSC client, and the periodic tick."""

    def __init__(self,
                 score: Score,
                 osc: PlayerOSCClient,
                 tick_hz: float = _TICK_HZ):
        self._score = score
        self._osc = osc
        self._tick_period = 1.0 / tick_hz
        self._state_machine = PlayerStateMachine()
        self._lock = threading.Lock()
        # Wallclock time at which playback time 0 occurred. None when paused
        # or idle. Set when transitioning to PLAYING.
        self._origin_wallclock: float = None  # type: ignore[assignment]
        self._stop_event = threading.Event()

    @property
    def state(self) -> State:
        return self._state_machine.state

    def _playback_t(self) -> float:
        if self._origin_wallclock is None:
            return self._state_machine.saved_t
        return time.time() - self._origin_wallclock

    def _apply(self, actions) -> None:
        for action in actions:
            if action.kind is ActionKind.START_AT:
                self._origin_wallclock = time.time() - action.t
                self._osc.start()
                _logger().info(
                    "PLAY from t=%.3f (origin_wallclock=%.3f)",
                    action.t, self._origin_wallclock)
            elif action.kind is ActionKind.STOP:
                self._origin_wallclock = None
                self._osc.stop()
                _logger().info("PAUSE at saved_t=%.3f",
                               self._state_machine.saved_t)
            elif action.kind is ActionKind.KILL:
                self._origin_wallclock = None
                self._osc.kill()
                _logger().info("KILL: state -> IDLE, saved_t=0")

    def short_press(self) -> None:
        with self._lock:
            actions = self._state_machine.short_press(self._playback_t())
            self._apply(actions)

    def long_press(self) -> None:
        with self._lock:
            actions = self._state_machine.long_press()
            self._apply(actions)

    def request_stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        """Block on the periodic tick until request_stop()."""
        while not self._stop_event.is_set():
            tick_start = time.time()
            with self._lock:
                if self._state_machine.state is State.PLAYING:
                    t = self._playback_t()
                    value = self._score.sample(t)
                    self._osc.fine_value(value)
            elapsed = time.time() - tick_start
            sleep_for = max(0.0, self._tick_period - elapsed)
            if self._stop_event.wait(timeout=sleep_for):
                break
        # Final tidy-up: if we exit while playing, send /stop so we don't
        # leave the tube modulating without a driver.
        if self._state_machine.state is not State.IDLE:
            _logger().info("Player shutting down; sending final /stop")
            self._osc.stop()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the score player")
    parser.add_argument(
        '-c', '--config',
        default=_DEFAULT_CONFIG,
        help="Path to irobot.conf (default: %(default)s)")
    parser.add_argument(
        '--root',
        default=None,
        help="OSC root (e.g. 'pwm1'). If omitted, looked up from the config.")
    parser.add_argument(
        '--score',
        default=None,
        help="Path to score CSV. If omitted, scores/<root>.csv is used.")
    parser.add_argument(
        '--osc-target',
        default="127.0.0.1:5005",
        help="host:port for the controller's OSC server "
             "(default: %(default)s)")
    parser.add_argument(
        '--button-pin',
        type=int,
        default=None,
        help="BCM pin for the start/stop switch. If omitted, looked up from "
             "the config (default 4 if unset).")
    parser.add_argument(
        '--mock-button',
        action='store_true',
        help="Read button events from stdin instead of GPIO. For testing "
             "without a Pi.")
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        help="Verbose logging; repeat up to three times")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    set_up_logging(args.verbose)
    log = _logger()

    # In mock-button mode the GPIO pin is moot; skip config lookup when the
    # CLI gives us enough to run.
    needs_config = args.root is None or (
        args.button_pin is None and not args.mock_button)
    if needs_config:
        config_root, config_pin = _resolve_from_config(args.config)
        root = args.root or config_root
        button_pin = args.button_pin if args.button_pin is not None \
            else config_pin
    else:
        root = args.root
        button_pin = args.button_pin if args.button_pin is not None else 4

    score_path = args.score or os.path.join(
        _DEFAULT_SCORES_DIR, "{}.csv".format(root))
    if not os.path.exists(score_path):
        log.error("Score file not found: %s", score_path)
        return 1
    score = Score.from_file(score_path)
    log.info("Loaded score %s: %d samples, duration=%.3fs, loop=%s",
             score_path, len(score._samples), score.duration, score.loop)

    osc_host, osc_port = parse_bind_host(args.osc_target, default_port=5005)
    osc = PlayerOSCClient(osc_host, osc_port, root)
    player = Player(score, osc)

    # Wire the button source.
    if args.mock_button:
        from plasma.player.mock_button import MockButtonWatcher
        watcher = MockButtonWatcher(
            on_short_press=player.short_press,
            on_long_press=player.long_press,
            on_quit=player.request_stop)
        watcher.start()
        pi = None
    else:
        import pigpio
        from plasma.player.button import ButtonWatcher
        pi = pigpio.pi()
        if not pi.connected:
            log.error("Could not connect to pigpiod")
            return 1
        watcher = ButtonWatcher(
            pi=pi,
            gpio_pin=button_pin,
            on_short_press=player.short_press,
            on_long_press=player.long_press)
        watcher.start()

    # SIGINT / SIGTERM both stop the run loop cleanly.
    def _shutdown(signum, frame):
        log.info("Got signal %s; shutting down", signum)
        player.request_stop()
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        player.run()
    finally:
        watcher.stop()
        if pi is not None:
            pi.stop()

    return 0


if __name__ == '__main__':
    sys.exit(main())
