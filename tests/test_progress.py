import pytest

from data.statistics import (accuracy_of, filter_history,
                             progress_series, compare_recent)


def entry(correct, total=10, mode="rotation", level="easy"):
    return {"tasks_correct": correct, "tasks_total": total,
            "mode": mode, "level": level, "points": 0, "total_seconds": 0}


def test_accuracy_of():
    assert accuracy_of(entry(7)) == 70
    assert accuracy_of(entry(0, total=0)) == 0.0


def test_filter_history():
    history = [entry(5, mode="rotation", level="easy"),
               entry(6, mode="matching", level="easy"),
               entry(7, mode="rotation", level="hard")]
    assert len(filter_history(history)) == 3
    assert len(filter_history(history, mode="rotation")) == 2
    assert len(filter_history(history, level="easy")) == 2
    assert len(filter_history(history, mode="rotation", level="hard")) == 1
    assert filter_history(history, mode="matching", level="hard") == []


def test_progress_series_is_chronological_and_limited():
    history = [entry(9), entry(5), entry(1)]   # новые первыми
    assert progress_series(history) == [10, 50, 90]
    assert progress_series(history, limit=2) == [50, 90]
    assert progress_series([]) == []


def test_compare_recent_needs_enough_sessions():
    assert compare_recent([entry(5)] * 3, recent_count=3) is None
    assert compare_recent([], recent_count=3) is None


def test_compare_recent_values():
    history = [entry(9), entry(8), entry(7),    # последние: 80%
               entry(5), entry(3)]              # ранние: 40%
    result = compare_recent(history, recent_count=3)
    assert result["recent_count"] == 3 and result["earlier_count"] == 2
    assert result["recent_accuracy"] == pytest.approx(80)
    assert result["earlier_accuracy"] == pytest.approx(40)
    assert result["difference"] == pytest.approx(40)


def test_compare_recent_negative_difference():
    history = [entry(2), entry(2), entry(2), entry(8)]
    assert compare_recent(history, recent_count=3)["difference"] == pytest.approx(-60)