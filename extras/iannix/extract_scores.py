#!/usr/bin/env python3
"""Extract per-tube score CSVs from the IAnnix performance file.

Best-effort parser. The IAnnix score is a JavaScript file that, in its
`madeThroughGUI()` block, lists `add curve` / `add cursor` blocks and a
`setmessage` line per cursor that names the OSC path. We extract:

  - Each cursor's associated base curve (the curve added immediately before
    the cursor, since IAnnix uses `setcurve current lastCurve`).
  - The OSC root from the `setmessage` URL.
  - The cursor's `setboundssource` rectangle (used to map the curve's
    y-coordinate into the [-1, 1] fine-value range).

For each cursor we write `scores/<root>.csv` containing `(t, fine_value)`
pairs at the curve's vertices. Cursor traversal speed is 1 (matching the
score's `run("speed 1")`).

CAVEAT: IAnnix's `collision_value_y` semantics involve geometry that the
author has not been able to fully verify without running IAnnix itself. For
flat base curves (which most of the cursors in `P-Tubes_w-SC_MM_G-2.iannix`
have) the extracted score will also be flat. Treat the output as a starting
point and edit the CSVs by hand to match the intended performance.
"""
import argparse
import math
import os
import re
import sys
from typing import List, Tuple


_DEFAULT_INPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "P-Tubes_w-SC_MM_G-2.iannix")
_DEFAULT_SCORES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "scores")


_CURVE_BLOCK_RE = re.compile(
    r'run\("add curve (\d+)"\);'
    r'.*?'
    r'var points\d+ = \[(.*?)\];',
    re.DOTALL)

_POINT_RE = re.compile(
    r'\{x:\s*(-?[\d.]+),\s*y:\s*(-?[\d.]+)')

_CURSOR_BLOCK_RE = re.compile(
    r'run\("add cursor (\d+)"\);'
    r'(.*?)'
    r'(?=run\("add (?:curve|cursor)|\Z)',
    re.DOTALL)

_BOUNDSSOURCE_RE = re.compile(
    r'setboundssource current\s+'
    r'([-\d.]+)\s+([-\d.]+)\s+'
    r'([-\d.]+)\s+([-\d.]+)\s+'
    r'([-\d.]+)\s+([-\d.]+)')

_OSC_PATH_RE = re.compile(r'osc://[^/]+/([^\s/]+)/')


def _parse_curves(text: str):
    curves = {}
    for match in _CURVE_BLOCK_RE.finditer(text):
        curve_id = match.group(1)
        block = match.group(2)
        points = [
            (float(x), float(y))
            for x, y in _POINT_RE.findall(block)
        ]
        if points:
            curves[curve_id] = points
    return curves


def _parse_cursors(text: str, curves):
    """Yield (cursor_id, root, curve_points, bounds_y_range) tuples."""
    # Track curves in source order so we can resolve `lastCurve`.
    curve_order = []
    for m in _CURVE_BLOCK_RE.finditer(text):
        curve_order.append(m.group(1))
    cursor_idx = 0
    for cm in _CURSOR_BLOCK_RE.finditer(text):
        cursor_id = cm.group(1)
        body = cm.group(2)
        bounds_match = _BOUNDSSOURCE_RE.search(body)
        osc_match = _OSC_PATH_RE.search(body)
        if bounds_match is None or osc_match is None:
            continue
        root = osc_match.group(1)
        y_min = float(bounds_match.group(3))
        y_max = float(bounds_match.group(4))
        # Cursors come after their referenced curve. In the GUI block they
        # appear in alternating order: curve, cursor (lastCurve = the curve
        # that was just added).
        if cursor_idx >= len(curve_order):
            continue
        curve_id = curve_order[cursor_idx]
        cursor_idx += 1
        points = curves.get(curve_id, [])
        if not points:
            continue
        yield cursor_id, root, points, (y_min, y_max)


def _curve_vertex_times(points: List[Tuple[float, float]],
                        speed: float = 1.0) -> List[float]:
    """At unit speed the cursor takes one second to cover one curve unit of
    arc length. Return cumulative time at each vertex."""
    times = [0.0]
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        total += math.hypot(dx, dy) / speed
        times.append(total)
    return times


def _fine_value_from_y(y: float, y_min: float, y_max: float) -> float:
    """Map curve y-coordinate through the boundsSource y-range into
    [-1, 1]. y_min → -1, y_max → +1, linear in between."""
    if y_max == y_min:
        return 0.0
    normalized = (y - y_min) / (y_max - y_min)  # → [0, 1] for in-range
    return max(-1.0, min(1.0, 2.0 * normalized - 1.0))


def _write_csv(path: str, samples, root: str, source_path: str) -> None:
    with open(path, 'w') as fp:
        fp.write("# scores/{}.csv\n".format(root))
        fp.write("# Extracted from {}\n".format(os.path.basename(source_path)))
        fp.write("# t_seconds, fine_value      "
                 "(fine_value in [-1, 1])\n")
        for t, v in samples:
            fp.write("{:.4f}, {:.6f}\n".format(t, v))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-i', '--input', default=_DEFAULT_INPUT,
        help="IAnnix score file (default: %(default)s)")
    parser.add_argument(
        '-o', '--out-dir', default=_DEFAULT_SCORES_DIR,
        help="Output directory for CSVs (default: %(default)s)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print("Input file not found: {}".format(args.input), file=sys.stderr)
        return 1
    os.makedirs(args.out_dir, exist_ok=True)
    with open(args.input, 'r') as fp:
        text = fp.read()
    curves = _parse_curves(text)

    written = []
    for _cursor_id, root, points, (y_min, y_max) in _parse_cursors(
            text, curves):
        times = _curve_vertex_times(points, speed=1.0)
        samples = [
            (t, _fine_value_from_y(p[1], y_min, y_max))
            for t, p in zip(times, points)
        ]
        # Ensure the score starts at t=0.
        if samples[0][0] != 0.0:
            t0 = samples[0][0]
            samples = [(t - t0, v) for t, v in samples]
        out_path = os.path.join(args.out_dir, "{}.csv".format(root))
        _write_csv(out_path, samples, root, args.input)
        ys = [p[1] for p in points]
        flat = (max(ys) - min(ys)) < 1e-6
        written.append((root, out_path, len(samples), flat))

    for root, path, n, flat in written:
        flag = " [FLAT]" if flat else ""
        print("wrote {} ({} samples){}".format(path, n, flag))
    print("\nNote: rows marked [FLAT] mean the underlying IAnnix base curve "
          "had no y-variation, so the extracted score is constant. The "
          "modulation in those tubes likely came from cursor/trigger-curve "
          "geometry that this extractor does not attempt to replicate. "
          "Edit the CSVs by hand or re-run with a richer extractor.",
          file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
