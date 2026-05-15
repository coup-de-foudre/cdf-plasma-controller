#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
# This file is part of the CdF Plasma Controller. See the top-level COPYING
# file for the AGPLv3 license terms.
#
"""Score-player state machine.

Pure logic — no threading, no I/O. The button-watching layer translates
hardware edges + timers into `press_down()` / `short_press()` / `long_press()`
calls and the runner translates the returned actions into OSC messages.

States: IDLE / PLAYING / PAUSED.

Boot safety: the machine always starts in IDLE regardless of the switch's
initial level. Only edge events (press_down / short / long) cause transitions.

Press-down semantics: pressing the button while PLAYING immediately pauses
the tube (per Jeff's request — without this the tube keeps modulating for
up to the full hold-threshold while we wait to classify short-vs-long). The
release-or-timer event that follows decides whether we stay PAUSED (short
press) or KILL back to IDLE (long press).
"""
import collections
import enum
from typing import List


class State(enum.Enum):
    IDLE = "IDLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"


class ActionKind(enum.Enum):
    START_AT = "START_AT"   # resume playback from `t` seconds, send /start
    STOP = "STOP"           # pause: stop the tube but keep `saved_t`
    KILL = "KILL"           # long-press: triple-stop and reset to t=0


# Functional namedtuple + default keeps us compatible with Python 3.5 on the
# deployed Pis (PEP 526 class-body annotations require 3.6+).
Action = collections.namedtuple('Action', ['kind', 't'])
Action.__new__.__defaults__ = (0.0,)


class PlayerStateMachine:
    """Press-driven score player state machine.

    Call `short_press(playback_t)` or `long_press()` when the button watcher
    classifies an event. `playback_t` is the runner's current playback time;
    the machine uses it to remember where to resume from on the next
    PAUSED → PLAYING transition.

    Each method returns the list of actions the runner should perform.
    """

    def __init__(self):
        self._state = State.IDLE
        self._saved_t = 0.0
        # True after press_down() pre-paused us from PLAYING. The next
        # short_press is then a no-op (we already stopped on the press
        # itself); cleared on any classification.
        self._pre_paused = False

    @property
    def state(self) -> State:
        return self._state

    @property
    def saved_t(self) -> float:
        return self._saved_t

    def press_down(self, playback_t: float) -> List[Action]:
        """Falling edge of the button. Only PLAYING reacts — we pre-pause
        the tube so the user gets immediate silence rather than waiting on
        the short/long classification."""
        if self._state is State.PLAYING:
            self._state = State.PAUSED
            self._saved_t = playback_t
            self._pre_paused = True
            return [Action(ActionKind.STOP)]
        return []

    def short_press(self, playback_t: float) -> List[Action]:
        if self._pre_paused:
            # press_down already stopped the tube from PLAYING; the release
            # confirms we stay PAUSED. No further OSC needed.
            self._pre_paused = False
            return []
        if self._state is State.IDLE:
            self._state = State.PLAYING
            self._saved_t = 0.0
            return [Action(ActionKind.START_AT, 0.0)]
        if self._state is State.PLAYING:
            self._state = State.PAUSED
            self._saved_t = playback_t
            return [Action(ActionKind.STOP)]
        if self._state is State.PAUSED:
            self._state = State.PLAYING
            return [Action(ActionKind.START_AT, self._saved_t)]
        raise AssertionError("unreachable state %r" % self._state)

    def long_press(self) -> List[Action]:
        self._pre_paused = False
        if self._state is State.IDLE:
            # Threshold fired with no playback to kill. Per the design, this
            # is a no-op so a stuck-on switch at boot doesn't auto-kill
            # something that isn't running.
            return []
        # PLAYING or PAUSED: kill immediately the moment the timer fires, so
        # the user gets instant audio/visual feedback that the hold registered.
        self._state = State.IDLE
        self._saved_t = 0.0
        return [Action(ActionKind.KILL)]
