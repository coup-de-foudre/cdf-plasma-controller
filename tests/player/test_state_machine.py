from plasma.player.state_machine import (
    Action, ActionKind, PlayerStateMachine, State)


def test_initial_state_is_idle():
    sm = PlayerStateMachine()
    assert sm.state is State.IDLE
    assert sm.saved_t == 0.0


def test_idle_short_press_starts_at_zero():
    sm = PlayerStateMachine()
    actions = sm.short_press(playback_t=0.0)
    assert sm.state is State.PLAYING
    assert actions == [Action(ActionKind.START_AT, 0.0)]


def test_playing_short_press_pauses_at_current_t():
    sm = PlayerStateMachine()
    sm.short_press(0.0)
    actions = sm.short_press(playback_t=4.2)
    assert sm.state is State.PAUSED
    assert sm.saved_t == 4.2
    assert actions == [Action(ActionKind.STOP)]


def test_paused_short_press_resumes_at_saved_t():
    sm = PlayerStateMachine()
    sm.short_press(0.0)         # IDLE -> PLAYING
    sm.short_press(7.5)         # PLAYING -> PAUSED at 7.5
    actions = sm.short_press(0.0)  # PAUSED -> PLAYING; playback_t ignored
    assert sm.state is State.PLAYING
    assert actions == [Action(ActionKind.START_AT, 7.5)]


def test_idle_long_press_is_noop():
    """Boot safety: a stuck-on switch at boot fires a long-press while IDLE,
    and the machine must not auto-kill anything."""
    sm = PlayerStateMachine()
    actions = sm.long_press()
    assert sm.state is State.IDLE
    assert actions == []


def test_playing_long_press_kills_and_resets():
    sm = PlayerStateMachine()
    sm.short_press(0.0)
    sm.short_press(3.0)         # PAUSED at 3.0 (just to seed saved_t)
    sm.short_press(0.0)         # back to PLAYING
    actions = sm.long_press()
    assert sm.state is State.IDLE
    assert sm.saved_t == 0.0
    assert actions == [Action(ActionKind.KILL)]


def test_paused_long_press_kills_and_resets():
    sm = PlayerStateMachine()
    sm.short_press(0.0)
    sm.short_press(2.0)         # PAUSED at 2.0
    actions = sm.long_press()
    assert sm.state is State.IDLE
    assert sm.saved_t == 0.0
    assert actions == [Action(ActionKind.KILL)]


def test_short_press_after_kill_starts_from_zero():
    sm = PlayerStateMachine()
    sm.short_press(0.0)
    sm.short_press(5.0)
    sm.long_press()             # IDLE, saved_t=0
    actions = sm.short_press(0.0)
    assert actions == [Action(ActionKind.START_AT, 0.0)]


# --- press_down semantics (Jeff's "immediate stop in PLAYING" feedback) ---


def test_press_down_from_idle_is_noop():
    sm = PlayerStateMachine()
    actions = sm.press_down(playback_t=0.0)
    assert sm.state is State.IDLE
    assert actions == []


def test_press_down_from_playing_immediately_pauses():
    sm = PlayerStateMachine()
    sm.short_press(0.0)         # IDLE -> PLAYING
    actions = sm.press_down(playback_t=4.2)
    assert sm.state is State.PAUSED
    assert sm.saved_t == 4.2
    assert actions == [Action(ActionKind.STOP)]


def test_press_down_then_short_press_stays_paused_without_extra_osc():
    """Release before threshold: we're already PAUSED from press_down, and
    the release must not flip us back to PLAYING."""
    sm = PlayerStateMachine()
    sm.short_press(0.0)         # PLAYING
    sm.press_down(4.2)          # PAUSED at 4.2
    actions = sm.short_press(playback_t=4.3)
    assert sm.state is State.PAUSED
    assert sm.saved_t == 4.2
    assert actions == []


def test_press_down_then_long_press_kills():
    sm = PlayerStateMachine()
    sm.short_press(0.0)         # PLAYING
    sm.press_down(4.2)          # PAUSED at 4.2 (pre-paused flag set)
    actions = sm.long_press()
    assert sm.state is State.IDLE
    assert sm.saved_t == 0.0
    assert actions == [Action(ActionKind.KILL)]


def test_press_down_from_paused_is_noop():
    """If we're already PAUSED (e.g. a previous short_press), pressing
    again should not emit a duplicate STOP; the release determines the
    next state via the existing PAUSED transitions."""
    sm = PlayerStateMachine()
    sm.short_press(0.0)
    sm.short_press(2.0)         # PAUSED at 2.0
    actions = sm.press_down(playback_t=2.0)
    assert sm.state is State.PAUSED
    assert sm.saved_t == 2.0
    assert actions == []
    # And the release still resumes from saved_t (no pre_paused interference).
    resume = sm.short_press(0.0)
    assert resume == [Action(ActionKind.START_AT, 2.0)]


def test_press_down_pre_paused_flag_cleared_after_resume_cycle():
    """After a press_down + short_press cycle, a *subsequent* short_press
    from PAUSED must resume normally (the pre_paused flag is one-shot)."""
    sm = PlayerStateMachine()
    sm.short_press(0.0)         # PLAYING
    sm.press_down(4.2)          # PAUSED, _pre_paused=True
    sm.short_press(4.3)         # stays PAUSED, _pre_paused cleared
    actions = sm.short_press(0.0)  # PAUSED -> PLAYING normally
    assert actions == [Action(ActionKind.START_AT, 4.2)]
