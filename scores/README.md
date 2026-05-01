# Scores

Per-tube playback scores for the score player (`score_player.py`).

One file per tube, named `<osc_root>.csv` (e.g. `pwm1.csv`). At runtime the
player picks `scores/<root>.csv` based on the `osc_roots` configured for
this Pi in `config/irobot.conf`.

## Format

A simple CSV of `t_seconds, fine_value` rows with linear interpolation
between samples:

```
# scores/pwm1.csv
# loop=false           (optional; defaults to loop=true)
0.000, 0.0
0.500, 0.8
1.250, -0.3
2.000, 0.0
```

Rules:

- Lines starting with `#` are comments. The header may set `loop=false` to
  play the score once and stop instead of looping.
- The first sample must be at `t=0`.
- Sample times must be monotonically non-decreasing.
- `fine_value` is the argument passed to the `/<root>/fine/value` OSC
  endpoint. The receiving controller maps it through the per-tube
  `frequency_spread` from `irobot.conf` to compute the actual PWM frequency
  offset, and clips to `[-1, 1]`.
- The player ticks at 50 Hz, sampling the curve and sending one OSC message
  per tick.

To produce a "duration + hold" effect, write two rows with the same value:

```
0.000, 0.0
2.000, 0.0      # hold at 0 for 2s
2.001, 0.7
4.001, 0.7      # hold at 0.7 for 2s
```

## Authoring

Hand-author a CSV. Anything that produces a sequence of `(time, value)`
rows works — a spreadsheet, a Python script, or text-edit by hand.

## Re-deriving from the IAnnix score

The scores in this directory were produced by capturing the actual OSC
output from a running IAnnix session (rather than reverse-engineering the
score's geometry from the source). To regenerate from scratch:

1. **Build IAnnix** (one-time). Mac: `brew install qt@5`, then clone
   <https://github.com/buzzinglight/IanniX> and run `qmake && make`. Two
   small source patches are needed on Apple Silicon to skip the x86_64-only
   Syphon framework — see `IanniX.pro:170` and `render/uirender.cpp:45` in
   that build for the pattern.

2. **Rewrite the production score for localhost** (so packets land on this
   Mac instead of the gallery LAN broadcast):

   ```
   python3 extras/iannix/rewrite_for_localhost.py \
       extras/iannix/P-Tubes_w-SC_MM_G-2.iannix \
       extras/iannix/P-Tubes_w-SC_MM_G-2.localhost.iannix
   ```

3. **Capture one full loop** with the OSC sink:

   ```
   python3 extras/iannix/osc_sink.py --duration 130 --out scores/capture
   ```

   In IAnnix: File → Open → the `*.localhost.iannix` copy, then play. The
   sink streams each `/<root>/fine/value` message into a per-tube CSV under
   `scores/capture/`. (That directory is gitignored — it's bulky and
   regenerable.)

4. **Simplify the captures** into committable scores:

   ```
   python3 extras/iannix/finalize_captures.py --tol 5e-3 --pad-to 120.0
   ```

   This trims to one loop (120 s), runs Ramer–Douglas–Peucker simplification
   at the given tolerance (each retained point reflects a real >tol
   deviation in the captured signal), drops any trailing duplicate near the
   loop boundary, and pads each file to end at exactly `(120, first_value)`
   so all tubes loop continuously and have identical duration. A built-in
   tail-smoothing rule for `pwm5` flattens an IAnnix loop-wrap discontinuity
   that would otherwise stress the driver electronics; pass
   `--smooth-tail-from pwm5:0` to disable.

5. **Verify** by overlaying capture vs simplified score:

   ```
   python3 extras/iannix/plot_scores.py --out docs/scores_vs_capture.png
   ```

`extras/iannix/extract_scores.py` is the original regex-based extractor.
It guesses which `var pointsN` array drives each cursor and produces flat
output for tubes whose base curves are flat horizontal lines — kept for
reference but no longer the source of truth. Use the capture flow above
instead.
