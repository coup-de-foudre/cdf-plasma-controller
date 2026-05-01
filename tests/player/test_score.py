import os
import tempfile

import pytest

from plasma.player.score import Score, ScoreError


def _write(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, 'w') as fp:
        fp.write(content)
    return path


def test_basic_interpolation():
    score = Score([(0.0, 0.0), (1.0, 1.0)])
    assert score.sample(0.0) == 0.0
    assert score.sample(0.5) == pytest.approx(0.5)
    assert score.sample(0.999) == pytest.approx(0.999)
    # At t == duration, a looping score wraps to the start.
    assert score.sample(1.0) == pytest.approx(0.0)


def test_non_looping_reaches_final_value():
    score = Score([(0.0, 0.0), (1.0, 1.0)], loop=False)
    assert score.sample(1.0) == pytest.approx(1.0)
    assert score.sample(2.0) == pytest.approx(1.0)  # clamped past the end


def test_three_segment_interpolation():
    score = Score([(0.0, 0.0), (1.0, 1.0), (2.0, -1.0)])
    assert score.sample(0.5) == pytest.approx(0.5)
    assert score.sample(1.5) == pytest.approx(0.0)
    assert score.sample(1.75) == pytest.approx(-0.5)


def test_loop_default_wraps():
    score = Score([(0.0, 0.0), (1.0, 1.0)])
    # With loop, t=1.5 wraps to t=0.5.
    assert score.sample(1.5) == pytest.approx(0.5)
    assert score.sample(2.5) == pytest.approx(0.5)


def test_no_loop_clamps_to_final_value():
    score = Score([(0.0, 0.0), (1.0, 0.7)], loop=False)
    assert score.sample(2.0) == pytest.approx(0.7)
    assert score.is_finished(2.0)
    assert not score.is_finished(0.5)


def test_step_and_hold_via_duplicate_values():
    # Jeff's "duration + hold" pattern.
    score = Score([(0.0, 0.0), (2.0, 0.0), (2.001, 0.7), (4.001, 0.7)])
    assert score.sample(1.0) == pytest.approx(0.0)
    assert score.sample(3.0) == pytest.approx(0.7)


def test_first_sample_must_be_t_zero():
    with pytest.raises(ScoreError):
        Score([(0.5, 0.0), (1.0, 1.0)])


def test_monotonic_time_required():
    with pytest.raises(ScoreError):
        Score([(0.0, 0.0), (1.0, 1.0), (0.5, -1.0)])


def test_empty_samples_rejected():
    with pytest.raises(ScoreError):
        Score([])


def test_from_file_parses_csv():
    path = _write(
        "# scores/test.csv\n"
        "0.0, 0.0\n"
        "1.0, 0.5\n"
        "2.0, 1.0\n"
    )
    try:
        score = Score.from_file(path)
        assert score.duration == 2.0
        assert score.loop is True
        assert score.sample(0.5) == pytest.approx(0.25)
    finally:
        os.remove(path)


def test_from_file_loop_false_header():
    path = _write(
        "# loop=false\n"
        "0.0, 0.0\n"
        "1.0, 1.0\n"
    )
    try:
        score = Score.from_file(path)
        assert score.loop is False
    finally:
        os.remove(path)


def test_from_file_skips_blank_and_comment_lines():
    path = _write(
        "\n"
        "# header\n"
        "0.0, 0.0\n"
        "\n"
        "# another comment\n"
        "1.0, 1.0\n"
    )
    try:
        score = Score.from_file(path)
        assert score.duration == 1.0
    finally:
        os.remove(path)
