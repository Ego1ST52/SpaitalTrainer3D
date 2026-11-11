from datetime import date

import pytest

from logic.achievements import (ACHIEVEMENTS, SKIN_UNLOCKS, newly_unlocked, progress,
                                unlocked, unlocked_skins)
from logic.cube_skins import SKINS
from logic.goals import best_streak, day_streak, goal_met, tasks_on

TODAY = date(2026, 11, 12)


def game(day, total=10, correct=7, mode="rotation", level="easy", hour=10):
    return {"mode": mode, "level": level, "played_at": f"2026-11-{day:02d}T{hour:02d}:00:00",
            "tasks_total": total, "tasks_correct": correct, "points": 50,
            "total_seconds": 60.0}


# ---------- цель дня и серия ----------
def test_tasks_on_sums_one_day():
    history = [game(12, 10), game(12, 5, hour=18), game(11, 10)]
    assert tasks_on(history, TODAY) == 15
    assert goal_met(history, TODAY, 15) and not goal_met(history, TODAY, 20)


def test_goal_zero_means_any_training_counts():
    assert goal_met([game(12, 3)], TODAY, 0)
    assert not goal_met([], TODAY, 0)


def test_streak_counts_consecutive_days():
    history = [game(10, 20), game(11, 20), game(12, 20)]
    assert day_streak(history, 20, TODAY) == 3


def test_streak_survives_until_today_is_played():
    history = [game(10, 20), game(11, 20)]             # сегодня ещё не играли
    assert day_streak(history, 20, TODAY) == 2


def test_streak_breaks_on_missed_day():
    history = [game(9, 20), game(11, 20), game(12, 20)]   # 10-го пропуск
    assert day_streak(history, 20, TODAY) == 2
    assert day_streak([game(12, 5)], 20, TODAY) == 0       # цель не выполнена


def test_best_streak():
    history = [game(1, 20), game(2, 20), game(3, 20), game(5, 20), game(6, 5)]
    assert best_streak(history, 20) == 3


# ---------- достижения ----------
def test_nothing_unlocked_for_new_player():
    assert unlocked([]) == set()
    assert unlocked_skins([]) == set()


def test_first_step_and_all_faces():
    history = [game(1, mode=m) for m in ("rotation", "matching", "projection")]
    assert {"first_step"} <= unlocked(history)
    assert progress("all_faces", history) == 3
    history.append(game(2, mode="construction"))
    assert "all_faces" in unlocked(history)


def test_flawless_needs_five_tasks():
    assert "flawless" not in unlocked([game(1, total=3, correct=3)])
    assert "flawless" in unlocked([game(1, total=5, correct=5)])
    assert "neon" in unlocked_skins([game(1, total=5, correct=5)])


def test_rotation_master_only_on_hard_rotation():
    assert "rotation_master" not in unlocked([game(1, 10, 10, level="medium")])
    assert "rotation_master" not in unlocked([game(1, 10, 10, mode="matching", level="hard")])
    assert "rotation_master" in unlocked([game(1, 10, 9, level="hard")])


def test_architect_and_marathon_progress_is_capped():
    history = [game(d, 5, 4, mode="construction") for d in range(1, 6)]   # 20 верных
    assert progress("architect", history) == 15 and "architect" in unlocked(history)
    big = [game(d, 20, 10) for d in range(1, 8)]                           # 140 заданий
    assert progress("marathon", big) == 100 and "pastel" in unlocked_skins(big)


def test_sharp_eye():
    assert "sharp_eye" not in unlocked([game(1, 40, 40)])        # мало заданий
    assert "sharp_eye" in unlocked([game(1, 50, 40)])            # 80% от 50
    assert "sharp_eye" not in unlocked([game(1, 50, 39)])


def test_streak_achievement_unlocks_jewel_skin():
    history = [game(d, 20) for d in (1, 2, 3)]
    assert "streak" in unlocked(history, goal=20)
    assert "streak" not in unlocked(history, goal=30)            # цель выше - не выполнена
    assert "jewel" in unlocked_skins(history, goal=20)


def test_newly_unlocked_lists_only_new_ones():
    before = [game(1, 4, 4)]
    after = before + [game(1, 5, 5, hour=12)]
    assert [a.key for a in newly_unlocked(before, after)] == ["flawless"]


def test_reward_skins_exist():
    assert set(SKIN_UNLOCKS) <= set(SKINS)
    assert len({a.key for a in ACHIEVEMENTS}) == len(ACHIEVEMENTS)


@pytest.mark.parametrize("achievement", ACHIEVEMENTS, ids=lambda a: a.key)
def test_progress_never_exceeds_target(achievement):
    huge = [game(d, 30, 30, mode=m, level="hard") for d in range(1, 10)
            for m in ("rotation", "construction")]
    assert progress(achievement.key, huge) <= achievement.target
