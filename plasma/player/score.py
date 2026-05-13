#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
# This file is part of the CdF Plasma Controller.  See the top-level COPYING
# file for the AGPLv3 license terms.
#
"""Score file format and sampler.

A score is a CSV file of `(t_seconds, fine_value)` pairs:

    # scores/pwm1.csv
    # loop=false        (optional; defaults to loop=true)
    0.000, 0.0
    0.500, 0.8
    1.250, -0.3

Values between rows are computed by linear interpolation. By default the
score loops; set `loop=false` in a header comment to play once and stop.
"""
from typing import List, Tuple


class ScoreError(Exception):
    pass


class Score:
    """A time-indexed sequence of fine-control values."""

    def __init__(self,
                 samples: List[Tuple[float, float]],
                 loop: bool = True):
        if not samples:
            raise ScoreError("Score must contain at least one sample")
        # Validate monotonic non-decreasing time, and the first sample is t=0.
        if samples[0][0] != 0.0:
            raise ScoreError(
                "First sample must be at t=0.0, got t=%s" % samples[0][0])
        for i in range(1, len(samples)):
            if samples[i][0] < samples[i - 1][0]:
                raise ScoreError(
                    "Sample times must be non-decreasing "
                    "(row %d: t=%s < previous t=%s)"
                    % (i, samples[i][0], samples[i - 1][0]))
        self._samples = samples
        self._loop = loop

    @classmethod
    def from_file(cls, path: str) -> 'Score':
        loop = True
        samples = []
        with open(path, 'r') as fp:
            for raw_line in fp:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    # Header directives. We only recognize `loop=...` for now.
                    body = line.lstrip('#').strip().lower()
                    if body.startswith('loop'):
                        _, _, value = body.partition('=')
                        value = value.strip()
                        if value in ('false', '0', 'no', 'off'):
                            loop = False
                        elif value in ('true', '1', 'yes', 'on', ''):
                            loop = True
                        else:
                            raise ScoreError(
                                "Unrecognized loop value: %r" % value)
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) != 2:
                    raise ScoreError(
                        "Expected 2 columns, got %d: %r" % (len(parts), line))
                try:
                    t = float(parts[0])
                    v = float(parts[1])
                except ValueError as e:
                    raise ScoreError(
                        "Could not parse row %r: %s" % (line, e))
                samples.append((t, v))
        return cls(samples, loop=loop)

    @property
    def loop(self) -> bool:
        return self._loop

    @property
    def duration(self) -> float:
        """Total score duration in seconds (time of last sample)."""
        return self._samples[-1][0]

    def is_finished(self, t: float) -> bool:
        """For non-looping scores: t has run past the final sample."""
        return (not self._loop) and t >= self.duration

    def sample(self, t: float) -> float:
        """Interpolated value at time `t`.

        For looping scores, `t` is wrapped modulo duration. For non-looping
        scores, `t` past the end is clamped to the final value.
        """
        if t < 0:
            t = 0.0
        if self._loop and self.duration > 0:
            t = t % self.duration
        elif t >= self.duration:
            return self._samples[-1][1]

        # Binary search for the right interval. Linear scan is fine for small
        # scores, but binary search keeps us honest at 50 Hz on the Pi for
        # multi-thousand-sample scores extracted from IAnnix.
        lo, hi = 0, len(self._samples) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self._samples[mid][0] < t:
                lo = mid + 1
            else:
                hi = mid
        # `lo` is the smallest index whose time is >= t.
        if lo == 0:
            return self._samples[0][1]
        t0, v0 = self._samples[lo - 1]
        t1, v1 = self._samples[lo]
        if t1 == t0:
            return v1
        frac = (t - t0) / (t1 - t0)
        return v0 + frac * (v1 - v0)
