"""Адаптивная сложность и «Моя тренировка»."""

import random

import pytest

from logic.adaptive import AdaptiveLevel, DOWN_AFTER, UP_AFTER
from logic.playlist import Playlist, build_steps, validate_plan
from logic.session import TrainingSession


# ---------- адаптивная сложность ----------
def test_three_correct_in_a_row_raises_level():
    a = AdaptiveLevel("easy")
    assert [a.record(True) for _ in range(UP_AFTER)] == [None] * (UP_AFTER - 1) + ["up"]
    assert a.level == "medium"


def test_two_wrong_in_a_row_lowers_level():
    a = AdaptiveLevel("hard")
    assert [a.record(False) for _ in range(DOWN_AFTER)] == [None] * (DOWN_AFTER - 1) + ["down"]
    assert a.level == "medium"


def test_streak_is_broken_by_other_answer():
    a = AdaptiveLevel("easy")
    for answer in (True, True, False, True, True):
        a.record(answer)
    assert a.level == "easy"                   # трёх верных подряд не было


def test_level_stays_within_bounds():
    a = AdaptiveLevel("hard")
    for _ in range(10):
        assert a.record(True) is None
    assert a.level == "hard"
    b = AdaptiveLevel("easy")
    for _ in range(10):
        assert b.record(False) is None
    assert b.level == "easy"


def test_counters_reset_after_change():
    a = AdaptiveLevel("easy")
    for _ in range(UP_AFTER):
        a.record(True)
    assert a.level == "medium"
    a.record(True)
    a.record(True)
    assert a.level == "medium"                 # счёт начался заново


def test_session_points_follow_task_level():
    session = TrainingSession("rotation", "easy", length=6, adaptive=AdaptiveLevel("easy"))
    for _ in range(3):
        session.record(True, 100)              # медленно: баллы без бонуса
    assert session.level_change == "up"
    assert session.current_level == "medium"
    session.record(True, 100)
    assert [r.points for r in session.results] == [10, 10, 10, 20]
    assert [r.level for r in session.results] == ["easy"] * 3 + ["medium"]


def test_summary_level_and_path():
    session = TrainingSession("rotation", "easy", length=8, adaptive=AdaptiveLevel("easy"))
    for answer in (True, True, True, True, True, True, False, False):
        session.record(answer, 5)
    # easy x3, medium x3, hard x2 -> поровну у easy и medium; берём более высокий
    assert session.levels_path == ["easy", "medium", "hard"]
    assert session.summary_level == "medium"


def test_session_without_adaptive_keeps_level():
    session = TrainingSession("matching", "hard", length=3)
    for _ in range(3):
        session.record(True, 1)
    assert session.current_level == "hard" and session.level_change is None
    assert session.summary_level == "hard"


# ---------- шаги тренировки ----------
def test_blocks_keep_fixed_mode_order():
    steps = build_steps(["projection", "rotation"], 3, "blocks")
    assert steps == [("rotation", 3), ("projection", 3)]


@pytest.mark.parametrize("seed", range(20))
def test_mixed_has_all_tasks_and_no_repeats_in_a_row(seed):
    modes = ["rotation", "matching", "construction"]
    steps = build_steps(modes, 5, "mixed", random.Random(seed))
    counts = {m: sum(c for mm, c in steps if mm == m) for m in modes}
    assert counts == {m: 5 for m in modes}
    assert all(count == 1 for _, count in steps)          # чередуются по одному
    assert all(a[0] != b[0] for a, b in zip(steps, steps[1:]))


def test_mixed_single_mode_is_one_step():
    assert build_steps(["rotation"], 3, "mixed") == [("rotation", 3)]


def test_validate_plan():
    good = {"modes": ["rotation"], "level": "easy", "per_mode": 3, "order": "blocks",
            "adaptive": False}
    assert validate_plan(good) is good
    for broken in ({**good, "modes": []}, {**good, "modes": ["chess"]},
                   {**good, "per_mode": 4}, {**good, "order": "random"},
                   {**good, "adaptive": "yes"}):
        with pytest.raises(ValueError):
            validate_plan(broken)


def test_playlist_merges_results_by_mode():
    playlist = Playlist([("rotation", 1), ("projection", 1), ("rotation", 1)], "easy")
    for mode, answer in (("rotation", True), ("projection", False), ("rotation", False)):
        session = TrainingSession(mode, "easy", length=1)
        session.record(answer, 3)
        playlist.finish_step(session)
    assert playlist.is_done and playlist.tasks_done == 3 == playlist.total_tasks
    merged = {s.mode: s for s in playlist.merged_by_mode()}
    assert set(merged) == {"rotation", "projection"}
    assert merged["rotation"].total == 2 and merged["rotation"].correct == 1
    assert playlist.correct == 1 and round(playlist.accuracy) == 33
