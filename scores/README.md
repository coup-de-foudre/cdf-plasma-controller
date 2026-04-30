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

## Re-extracting from the IAnnix score

```
python3 extras/iannix/extract_scores.py
```

This reads `extras/iannix/P-Tubes_w-SC_MM_G-2.iannix` and writes one CSV
per cursor it finds.

**Caveat**: the extractor is best-effort. IAnnix's `collision_value_y`
involves cursor-vs-trigger-curve geometry that the extractor does not
faithfully replicate. The current implementation:

1. Parses each cursor's associated base curve from the IAnnix file.
2. Walks the curve at speed 1 (matching the IAnnix `speed` setting).
3. Maps each vertex's y-coordinate through the cursor's
   `setboundssource` y-range into `[-1, 1]`.

For tubes whose IAnnix base curve is a flat horizontal line, this yields a
constant score (logged as `[FLAT]` when running the extractor). The
artistic content for those tubes likely came from cursor/trigger-curve
geometry that this extractor doesn't replicate. Treat the output as a
starting point and edit the CSVs by hand to match the intended performance.
