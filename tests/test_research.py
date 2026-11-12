"""Подсказки, опыт «время против угла», тест до/после, рекорды, отчёт HTML,
работа над ошибками и порядок сборки в демо."""

import random

import pytest

from core.preferences import Preferences
from logic.assessment import (TEST_SEEDS, TEST_STEPS, compare, make_test, summarize_test,
                              validate_assessment)
from logic.experiment import (MIN_ANSWERS, angle_table, conclusion, experiment_points,
                              trend)
from logic.hints import hints_left, pick_hint, points_with_hints
from logic.html_report import build_html, write_html
from logic.insights import PRACTICE_PER_MODE, practice_steps
from logic.leaderboard import leaderboard
from logic.matching_tasks import MatchingTaskGenerator, rotation_angle
from logic.rotations import IDENTITY, all_orientations, rotate
from logic.session import TrainingSession


# ---------- подсказки ----------
def test_hint_never_removes_the_answer_and_leaves_two():
    rng = random.Random(1)
    for count in (3, 4, 5):
        for correct in range(count):
            removed = set()
            while (index := pick_hint(correct, count, removed, rng)) is not None:
                assert index != correct and index not in removed
                removed.add(index)
            assert count - len(removed) == 2
            assert hints_left(count, removed) == 0


def test_hint_halves_points_and_is_logged():
    assert points_with_hints(25, 0) == 25
    assert points_with_hints(25, 1) == 12
    assert points_with_hints(25, 2) == 6
    plain, helped = TrainingSession("rotation", "easy", 2), TrainingSession("rotation", "easy", 2)
    full = plain.record(True, 1.0, ("axis:x",))
    half = helped.record(True, 1.0, ("axis:x",), hints=1)
    assert half == full // 2
    assert helped.results[0].tags == ("axis:x", "hint")
    assert plain.results[0].tags == ("axis:x",)


# ---------- угол поворота в «Одинаковых фигурах» ----------
def test_rotation_angle_of_all_24_rotations():
    angles = sorted(rotation_angle(m) for m in all_orientations())
    # тождественный; 6 поворотов на 90° вокруг осей граней; 8 на 120° вокруг
    # диагоналей; 3 + 6 на 180° (вокруг осей граней и рёбер)
    assert {a: angles.count(a) for a in set(angles)} == {0: 1, 90: 6, 120: 8, 180: 9}
    assert rotation_angle(rotate(IDENTITY, "y", 90)) == 90
    assert rotation_angle(rotate(IDENTITY, "x", 180)) == 180


def test_matching_task_carries_turn_tag():
    gen = MatchingTaskGenerator(seed=4)
    for _ in range(30):
        task = gen.generate("medium")
        assert f"turn:{task.turn_angle}" in task.tags
        assert task.turn_angle in (0, 90, 120, 180)


# ---------- опыт ----------
def _entry(angle, seconds, correct=True, mode="matching", extra=()):
    return {"mode": mode, "correct": correct, "seconds": seconds,
            "tags": [f"turn:{angle}", *extra]}


def test_experiment_uses_only_clean_correct_matching_answers():
    log = [_entry(90, 5), _entry(90, 7), _entry(180, 9), _entry(0, 3, correct=False),
           _entry(0, 3, mode="rotation"), _entry(120, 4, extra=("hint",)),
           _entry(120, 500)]
    points = experiment_points(log)
    assert sorted(points) == [(90, 5), (90, 7), (180, 9)]
    assert angle_table(points) == {90: (2, 6.0), 180: (1, 9.0)}


def test_experiment_trend_and_conclusion():
    points = [(a, 3 + a / 30) for a in (0, 90, 120, 180) for _ in range(4)]
    a, b = trend(points)
    assert a == pytest.approx(3) and b * 90 == pytest.approx(3)
    assert "Эффект есть" in conclusion(points)
    assert "мало данных" in conclusion(points[:MIN_ANSWERS - 1])
    flat = [(a, 5.0) for a in (0, 90, 180) for _ in range(5)]
    assert "почти не зависит" in conclusion(flat)
    assert trend([(90, 1), (90, 2)]) is None


# ---------- тест до и после ----------
def _passed(stage, answers):
    playlist = make_test(stage)
    while not playlist.is_done:
        mode, count = playlist.current
        session = TrainingSession(mode, "medium", count)
        for _ in range(count):
            session.record(next(answers), 10.0)
        playlist.finish_step(session)
    return playlist


def test_tests_have_fixed_and_different_tasks():
    pre, post = make_test("pre"), make_test("post")
    assert pre.steps == post.steps == TEST_STEPS and pre.adaptive is None
    assert pre.stage == "pre" and post.stage == "post"
    assert set(TEST_SEEDS["pre"].values()).isdisjoint(TEST_SEEDS["post"].values())
    with pytest.raises(ValueError):
        make_test("middle")


def test_test_summary_compare_and_prefs():
    from datetime import date
    pre = summarize_test(_passed("pre", iter([True, False, False] * 5)), date(2026, 11, 1))
    post = summarize_test(_passed("post", iter([True, True, False] * 5)), date(2026, 11, 12))
    assert pre["accuracy"] == pytest.approx(33.3) and post["accuracy"] == pytest.approx(66.7)
    assert pre["modes"]["rotation"] == pytest.approx(33.3)
    rows = compare(pre, post)
    assert rows[0][0] == "Точность" and rows[0][3] == "+33%" and rows[0][4] is True
    assert rows[1][3] == "без изменений" and rows[1][4] is None
    prefs = Preferences()
    prefs.set("assessment", {"pre": pre, "post": post})
    with pytest.raises(ValueError):
        validate_assessment({"pre": {"accuracy": 50}})
    with pytest.raises(ValueError):
        validate_assessment({"middle": pre})


def test_test_playlist_uses_fixed_seeds_and_no_hints():
    from interface.game_common import new_training
    playlist = make_test("post")
    session, seed = new_training("rotation", "medium", playlist=playlist)
    assert seed == TEST_SEEDS["post"]["rotation"] and session.no_hints


# ---------- рекорды ----------
def _game(mode, points, correct, total=10):
    return {"mode": mode, "points": points, "tasks_correct": correct, "tasks_total": total}


def test_leaderboard_order_and_filter():
    players = [("Аня", [_game("rotation", 150, 9), _game("matching", 90, 6)]),
               ("Борис", [_game("rotation", 200, 7)]),
               ("Вика", [_game("matching", 150, 10)]),
               ("Гоша", [])]
    rows = leaderboard(players)
    assert [r.name for r in rows] == ["Борис", "Вика", "Аня"]
    assert [r.place for r in rows] == [1, 2, 3]
    assert rows[2].total == 240 and rows[2].accuracy == 75 and rows[2].trainings == 2
    assert [r.name for r in leaderboard(players, "matching")] == ["Вика", "Аня"]
    assert leaderboard(players, "nets") == []


# ---------- отчёт HTML ----------
def test_html_report_is_self_contained(tmp_path):
    history = [{"mode": "rotation", "level": "easy", "played_at": "2026-11-12T10:00:00",
                "tasks_total": 10, "tasks_correct": 8, "points": 120, "total_seconds": 60}]
    log = [_entry(90, 6.0)] * 3
    assessment = {"pre": {"date": "2026-11-01", "accuracy": 50.0, "seconds": 12.0,
                          "modes": {}}}
    page = build_html([("Аня <script>", history, log, assessment), ("Борис", [], [], None)])
    assert page.startswith("<!doctype html>") and "<svg" in page
    assert "<script>" not in page and "Аня &lt;script&gt;" in page
    assert "Входной тест" in page and "Итоговый тест ещё не пройден" in page
    assert "http" not in page                      # всё внутри файла, интернет не нужен
    path = write_html(page, tmp_path)
    assert path.read_text(encoding="utf-8") == page and path.suffix == ".html"


# ---------- работа над ошибками ----------
def test_practice_steps_pick_weakest_modes():
    def tasks(mode, right, wrong):
        return ([{"mode": mode, "correct": True, "tags": []}] * right
                + [{"mode": mode, "correct": False, "tags": []}] * wrong)
    log = (tasks("rotation", 9, 1) + tasks("matching", 5, 5) + tasks("nets", 7, 3)
           + tasks("count", 1, 2) + tasks("projection", 6, 4) + tasks("shadow", 4, 6))
    # count - всего 3 задания (мало для вывода), rotation - 90% (не трудный)
    assert practice_steps(log) == [("shadow", PRACTICE_PER_MODE),       # 40%
                                   ("matching", PRACTICE_PER_MODE),     # 50%
                                   ("projection", PRACTICE_PER_MODE)]   # 60%
    assert practice_steps(tasks("rotation", 10, 0)) == []
    assert practice_steps([]) == []


# ---------- демо ----------
def test_demo_build_order_is_buildable():
    from interface.demo import build_order
    from logic.construction import Build
    from logic.shapes import random_shape
    rng = random.Random(5)
    for _ in range(30):
        shape = random_shape(rng, 7)
        build = Build(20)
        order = build_order(shape, lambda cell, placed: _can(build, cell, placed))
        assert sorted(order) == sorted(shape)
        for cell in order:
            assert build.add(cell)


def _can(build, cell, placed):
    probe = type(build)(build.max_cubes)
    probe.cells = set(placed)
    return probe.can_add(cell)
