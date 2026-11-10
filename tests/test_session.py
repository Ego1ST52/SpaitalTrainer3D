import pytest

from logic.scoring import task_points
from logic.session import TrainingSession, format_duration


def test_instant_correct_answer_gets_full_bonus():
    assert task_points("easy", True, 0) == 15      # 10 + 50%
    assert task_points("hard", True, 0) == 45      # 30 + 50%


def test_bonus_shrinks_with_time():
    assert task_points("medium", True, 22.5) == 25  # половина бонуса


def test_no_bonus_after_time_limit():
    assert task_points("easy", True, 30) == 10
    assert task_points("easy", True, 500) == 10


def test_wrong_answer_gives_zero():
    assert task_points("hard", False, 1) == 0


def test_scoring_rejects_bad_input():
    with pytest.raises(ValueError):
        task_points("impossible", True, 1)
    with pytest.raises(ValueError):
        task_points("easy", True, -1)


def test_session_totals():
    s = TrainingSession("rotation", "easy", length=4)
    s.record(True, 0)       # 15
    s.record(False, 10)     # 0
    s.record(True, 30)      # 10
    assert s.total == 3
    assert s.correct == 2
    assert s.wrong == 1
    assert s.points == 25
    assert s.accuracy == pytest.approx(200 / 3)
    assert s.total_time == 40
    assert s.average_time == pytest.approx(40 / 3)
    assert not s.is_finished


def test_session_finishes_and_rejects_extra_results():
    s = TrainingSession("matching", "easy", length=2)
    s.record(True, 5)
    s.record(True, 5)
    assert s.is_finished
    with pytest.raises(ValueError):
        s.record(True, 5)


def test_empty_session_has_zero_stats():
    s = TrainingSession("rotation", "easy")
    assert s.accuracy == 0.0 and s.average_time == 0.0 and s.points == 0


def test_invalid_length():
    with pytest.raises(ValueError):
        TrainingSession("rotation", "easy", length=0)


def test_format_duration():
    assert format_duration(0) == "00:00"
    assert format_duration(65.4) == "01:05"
    assert format_duration(600) == "10:00"