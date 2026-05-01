#!/usr/bin/env python3
"""Stacked comparison plot: raw IanniX capture vs the simplified
committable score.

Used to verify (and document, for the PR) that the RDP-simplified score in
`scores/<root>.csv` faithfully reproduces the IanniX capture in
`scores/capture/<root>.csv`.
"""
import argparse
import os
import sys
from typing import List, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


ROOTS = ["pwm1", "pwm2", "pwm3", "pwm4", "pwm5", "pwm6", "pwm7"]

# Mirror finalize_captures.TUBE_NAMES so the plot is self-documenting.
TUBE_NAMES = {
    "pwm1": "XC SUBA",
    "pwm2": "AKI",
    "pwm3": "AKN",
    "pwm4": "XP",
    "pwm5": "SC1",
    "pwm6": "SC2",
    "pwm7": "SC3",
}


def load(path: str) -> Tuple[List[float], List[float]]:
    ts: List[float] = []
    vs: List[float] = []
    with open(path) as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 2:
                continue
            ts.append(float(parts[0]))
            vs.append(float(parts[1]))
    return ts, vs


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture-dir', default='scores/capture')
    p.add_argument('--player-dir', default='scores/capture_player',
                   help='Optional: per-tube CSVs captured from the score '
                        'player itself; overlaid as a third trace if '
                        'present')
    p.add_argument('--scores-dir', default='scores')
    p.add_argument('--max-t', type=float, default=120.0,
                   help='Plot range upper bound on the x-axis (s)')
    p.add_argument('--player-max-t', type=float, default=140.0,
                   help='How much player capture to show (s); >max-t shows '
                        'the loop wrap')
    p.add_argument('--out', default='docs/scores_vs_capture.png')
    p.add_argument('--dpi', type=int, default=160)
    args = p.parse_args()

    fig, axes = plt.subplots(
        len(ROOTS), 1,
        figsize=(13, 11),
        sharex=True,
        gridspec_kw={'hspace': 0.18})
    fig.patch.set_facecolor('white')

    raw_color = '#5a5a5a'
    fin_color = '#1a8a4f'
    play_color = '#c43d3d'
    accent_color = '#c43d3d'

    # Detect any player traces up front so the legend reflects what we
    # actually plot.
    have_player = any(
        os.path.exists(os.path.join(args.player_dir, '{}.csv'.format(r)))
        for r in ROOTS)

    x_max = max(args.max_t, args.player_max_t if have_player else args.max_t)

    for ax, root in zip(axes, ROOTS):
        ax.set_facecolor('#fafafa')
        for spine in ('top', 'right'):
            ax.spines[spine].set_visible(False)
        ax.spines['left'].set_color('#cccccc')
        ax.spines['bottom'].set_color('#cccccc')
        ax.tick_params(colors='#888888', labelsize=8)
        ax.set_xlim(0, x_max)
        ax.set_ylim(-1.15, 1.15)
        ax.set_yticks([-1, 0, 1])
        ax.axhline(0, color='#cccccc', linewidth=0.6, zorder=0)
        if have_player:
            ax.axvline(args.max_t, color='#bbbbbb', linewidth=0.8,
                       linestyle=':', zorder=1)

        raw_path = os.path.join(args.capture_dir, '{}.csv'.format(root))
        fin_path = os.path.join(args.scores_dir, '{}.csv'.format(root))
        play_path = os.path.join(args.player_dir, '{}.csv'.format(root))

        if os.path.exists(raw_path):
            t, v = load(raw_path)
            t_trim = [tt for tt in t if tt <= args.max_t]
            v_trim = v[:len(t_trim)]
            ax.plot(
                t_trim, v_trim,
                color=raw_color, linewidth=1.4, alpha=0.55,
                solid_capstyle='round',
                label='IanniX capture (raw)' if root == ROOTS[0] else None,
                zorder=2)

        if os.path.exists(play_path):
            t, v = load(play_path)
            t_trim = [tt for tt in t if tt <= args.player_max_t]
            v_trim = v[:len(t_trim)]
            ax.plot(
                t_trim, v_trim,
                color=play_color, linewidth=0.9, alpha=0.85,
                label='Player output' if root == ROOTS[0] else None,
                zorder=2.5)

        if os.path.exists(fin_path):
            t, v = load(fin_path)
            ax.plot(
                t, v,
                color=fin_color, linewidth=1.6,
                label='Committed score (RDP)' if root == ROOTS[0] else None,
                zorder=3)
            ax.plot(
                t, v,
                linestyle='None', marker='o',
                markersize=3.2, markerfacecolor=fin_color,
                markeredgecolor='white', markeredgewidth=0.6,
                zorder=4)
            n_pts = len(t)
        else:
            n_pts = 0

        name = TUBE_NAMES.get(root, '')
        label = '{}\n{}'.format(root.upper(), name) if name else root.upper()
        ax.set_ylabel(
            label,
            rotation=0, ha='right', va='center',
            fontsize=10, fontweight='bold',
            color='#333333', labelpad=20,
            linespacing=1.3)

        ax.text(
            0.995, 0.93,
            '{} points'.format(n_pts),
            transform=ax.transAxes, ha='right', va='top',
            fontsize=8, color=accent_color,
            fontweight='bold')

    axes[-1].set_xlabel('t (seconds)', fontsize=10, color='#333333')
    axes[0].legend(
        loc='lower left', frameon=False, fontsize=9,
        ncol=3 if have_player else 2,
        bbox_to_anchor=(0, 1.02))

    if have_player:
        title = ('IanniX capture vs committed score vs player output '
                 '(dotted line = loop boundary at 120 s)')
    else:
        title = 'IanniX score: raw capture vs RDP-simplified committed score'
    fig.suptitle(title, fontsize=12, fontweight='bold',
                 color='#222222', y=0.995)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(args.out, dpi=args.dpi, facecolor='white')
    print('wrote {} ({} dpi)'.format(args.out, args.dpi))
    return 0


if __name__ == '__main__':
    sys.exit(main())
