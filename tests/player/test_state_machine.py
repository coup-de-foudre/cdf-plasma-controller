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
