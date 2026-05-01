#!/usr/bin/env python3
"""Truncate and dedupe captured CSVs into committable scores.

Reads `scores/capture/<root>.csv` (raw 50 Hz IanniX captures), drops rows
past `--max-t`, and run-length-collapses constant-value runs so the
resulting CSV is much smaller while exactly preserving the shape under
linear interpolation.

For each maximal run of equal values we keep the first and the last sample
of the run (the endpoints), so the score loader's linear interpolation
sees the same flat segment without storing thousands of duplicate rows.

Usage:
    python3 extras/iannix/finalize_captures.py
    python3 extras/iannix/finalize_captures.py --max-t 120 \\
        --in scores/capture --out scores
"""
import argparse
import os
import sys
from typing import List, Tuple


def read_csv(path: str) -> List[Tuple[float, float]]:
    rows: List[Tuple[float, float]] = []
    with open(path) as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 2:
                continue
            rows.append((float(parts[0]), float(parts[1])))
    return rows


def truncate(rows, max_t):
    return [(t, v) for t, v in rows if t <= max_t]


def rdp(rows, tol):
    """Ramer-Douglas-Peucker polyline simplification.

    For each range [a, b], find the interior point i with maximum vertical
    deviation from the chord rows[a] -> rows[b]. (Vertical, not
    perpendicular: t and v are different units, so vertical distance in v
    is the natural metric here.) If max deviation <= tol, collapse the
    range to its endpoints. Otherwise split at i and recurse on both
    halves.
    """
    n = len(rows)
    if n < 3:
        return list(rows)
    keep = [False] * n
    keep[0] = keep[-1] = True

    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        t_a, v_a = rows[a]
        t_b, v_b = rows[b]
        dt = t_b - t_a
        max_dev = 0.0
        max_i = -1
        for i in range(a + 1, b):
            t_i, v_i = rows[i]
            if dt > 0:
                v_chord = v_a + (t_i - t_a) / dt * (v_b - v_a)
            else:
                v_chord = v_a
            dev = abs(v_i - v_chord)
            if dev > max_dev:
                max_dev = dev
                max_i = i
        if max_dev > tol and max_i > 0:
            keep[max_i] = True
            stack.append((a, max_i))
            stack.append((max_i, b))

    return [rows[i] for i, k in enumerate(keep) if k]


def write_csv(path: str, rows, root: str) -> None:
    # Anchor t=0 if needed.
    t0 = rows[0][0] if rows else 0.0
    with open(path, 'w') as fp:
        fp.write("# scores/{}.csv\n".format(root))
        fp.write("# Captured from IanniX, truncated and deduplicated\n")
        fp.write("# t_seconds, fine_value      "
                 "(fine_value in [-1, 1])\n")
        for t, v in rows:
            fp.write("{:.4f}, {:.6f}\n".format(t - t0, v))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--in', dest='in_dir', default='scores/capture',
        help='Capture directory (default: %(default)s)')
    parser.add_argument(
        '--out', default='scores',
        help='Output directory (default: %(default)s)')
    parser.add_argument(
        '--max-t', type=float, default=120.0,
        help='Truncate samples after this many seconds '
             '(default: %(default)s)')
    parser.add_argument(
        '--tol', type=float, default=5e-3, metavar='TOL',
        help='RDP simplification tolerance. A point is kept iff its '
             'vertical deviation from the chord between its neighbors '
             'in the polyline exceeds TOL. Smaller -> more rows, more '
             'fidelity. Default: %(default)s')
    parser.add_argument(
        '--pad-to', type=float, default=None, metavar='T',
        help='After simplification, append a final row at t=T whose value '
             'matches the t=0 sample (so the loop wraps continuously and '
             'all scores have identical duration). Typically equal to '
             '--max-t.')
    parser.add_argument(
        '--smooth-tail-from', action='append', default=[],
        metavar='ROOT:T',
        help='For the named tube, drop all RDP samples after t=T before '
             'padding, so the final segment is a clean linear ramp from '
             'the last surviving point to (--pad-to, first_value). May be '
             'repeated. Built-in default smooths the pwm5 loop-wrap '
             'discontinuity; pass --smooth-tail-from pwm5:0 to disable.')
    args = parser.parse_args()

    if not os.path.isdir(args.in_dir):
        print("input dir does not exist: {}".format(args.in_dir),
              file=sys.stderr)
        return 1
    os.makedirs(args.out, exist_ok=True)

    # Default tail-smoothing: pwm5's IanniX loop wraps with a ~22% spike
    # in 5 ms. Drop trailing samples after t=113.5 so the closure is a
    # ~6 s linear ramp instead — much gentler on the driver electronics.
    smooth_tail = {"pwm5": 113.5}
    for spec in args.smooth_tail_from:
        if ':' not in spec:
            print("ignoring malformed --smooth-tail-from {}".format(spec),
                  file=sys.stderr)
            continue
        root, _, t_str = spec.partition(':')
        smooth_tail[root.strip()] = float(t_str)

    for fname in sorted(os.listdir(args.in_dir)):
        if not fname.endswith('.csv'):
            continue
        root = fname[:-4]
        in_path = os.path.join(args.in_dir, fname)
        out_path = os.path.join(args.out, fname)

        rows = read_csv(in_path)
        n_raw = len(rows)
        rows = truncate(rows, args.max_t)
        n_trunc = len(rows)
        rows = rdp(rows, args.tol)

        # Per-tube tail-smoothing override: drop trailing samples beyond
        # the configured cutoff so a clean linear ramp closes the loop.
        cutoff = smooth_tail.get(root)
        if cutoff is not None and cutoff > 0:
            rows = [(t, v) for t, v in rows if t <= cutoff]

        if args.pad_to is not None and rows:
            # Anchor durations across all tubes by ending at exactly
            # (pad_to, first_value). Drop any trailing rows that are
            # already near first_value or near pad_to — they'd otherwise
            # leave a redundant duplicate point right before the explicit
            # endpoint.
            first_value = rows[0][1]
            pad_eps_v = max(args.tol, 1e-4)
            pad_eps_t = 0.5 * args.tol if args.tol > 0 else 1e-3
            while len(rows) > 1:
                t, v = rows[-1]
                near_endpoint_t = (args.pad_to - t) <= pad_eps_t
                near_endpoint_v = abs(v - first_value) <= pad_eps_v
                if near_endpoint_t or near_endpoint_v:
                    rows.pop()
                else:
                    break
            rows.append((args.pad_to, first_value))
        n_final = len(rows)

        if not rows:
            print("[{}] no rows after truncate; skipping".format(root))
            continue
        write_csv(out_path, rows, root)
        print("[{}] {} raw -> {} trunc -> {} simplified "
              "  duration={:.2f}s".format(
                  root, n_raw, n_trunc, n_final,
                  rows[-1][0] - rows[0][0]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
