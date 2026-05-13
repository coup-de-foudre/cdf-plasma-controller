#
# Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
#
# This file is part of the CdF Plasma Controller. See the top-level COPYING
# file for the AGPLv3 license terms.
#
"""Score-player state machine.

Pure logic — no threading, no I/O. The button-watching layer translates
hardware edges + timers into `short_press()` / `long_press()` calls and the
runner translates the returned actions into OSC messages.

States: IDLE / PLAYING / PAUSED.

Boot safety: the machine always starts in IDLE regardless of the switch's
initial level. Only edge events (short or long press) cause transitions.
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

    @property
    def state(self) -> State:
        return self._state

    @property
    def saved_t(self) -> float:
        return self._saved_t

    def short_press(self, playback_t: float) -> List[Action]:
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
