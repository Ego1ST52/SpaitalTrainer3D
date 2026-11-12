"""Источник заданий, «Повторить ошибки», «Продолжить тренировку», курс,
задания для класса, новые режимы «Что изменилось?» и «Взгляд наблюдателя»,
«Блиц» и озвучка."""

from datetime import date, datetime

import pytest

from core.preferences import Preferences, prefs
from logic.changed import ChangedTaskGenerator, is_answer
from logic.class_tasks import add_assignment, limits, make_assignment, results_for
from logic.course import LESSONS, advance, lesson_passed, lesson_playlist, state
from logic.matching_tasks import MatchingTaskGenerator
from logic.observer import ObserverTaskGenerator, Tower, view_from
from logic.resume import describe, restore, snapshot, validate_resume
from logic.review import (BOX_DAYS, MAX_PER_REVIEW, due_items, review_plan, update_review,
                          validate_review)
from logic.session import TrainingSession
from logic.shapes import is_connected
from logic.task_source import ReviewSource, TrackingSource, replay
from logic.training_code import make_code, parse_code


def factory(seed):
    return MatchingTaskGenerator(seed=seed)


# ---------- источник заданий ----------
def test_tracking_keys_replay_the_same_tasks():
    source = TrackingSource(factory, 77)
    levels = ["easy", "easy", "medium", "hard", "medium"]
    tasks = [source.generate(level) for level in levels]
    assert source.keys[2] == (77, ("easy", "easy", "medium"))
    for task, key in zip(tasks, source.keys):
        assert replay(factory, *key) == task


def test_fast_forward_continues_where_it_stopped():
    full = TrackingSource(factory, 5)
    tasks = [full.generate("easy") for _ in range(4)]
    resumed = TrackingSource(factory, 5)
    resumed.fast_forward(["easy"] * 3)
    assert resumed.generate("easy") == tasks[3]


def test_review_source_gives_saved_tasks():
    full = TrackingSource(factory, 9)
    tasks = [full.generate(level) for level in ("easy", "medium", "medium")]
    items = [{"seed": 9, "levels": list(full.keys[2][1])},
             {"seed": 9, "levels": list(full.keys[0][1])}]
    source = ReviewSource(factory, items)
    assert source.generate("hard") == tasks[2]
    assert source.generate("easy") == tasks[0]


# ---------- повторение ошибок ----------
def test_review_boxes():
    today = date(2026, 11, 12)
    key = (3, ("easy",))
    items = update_review([], "rotation", [(key, False), ((3, ("easy", "easy")), True)], today)
    assert len(items) == 1 and items[0]["box"] == 0 and items[0]["due"] == "2026-11-13"
    assert due_items(items, today) == []
    assert due_items(items, date(2026, 11, 13)) == items
    # обычная тренировка: верный ответ на то же задание ничего не меняет
    assert update_review(items, "rotation", [(key, True)], today) == items
    day = date(2026, 11, 13)
    for box in range(1, len(BOX_DAYS)):
        items = update_review(items, "rotation", [(key, True)], day, reviewing=True)
        assert items[0]["box"] == box
    items = update_review(items, "rotation", [(key, True)], day, reviewing=True)
    assert items == []                                   # выучено
    again = update_review([{"mode": "rotation", "seed": 3, "levels": ["easy"], "box": 2,
                            "due": "2026-11-12"}], "rotation", [(key, False)], day,
                          reviewing=True)
    assert again[0]["box"] == 0                          # ошибка - снова в первую коробку
    assert update_review([], "blitz", [(key, False)], today) == []


def test_review_plan_groups_by_mode():
    items = [{"mode": m, "seed": i, "levels": ["easy"], "box": 0, "due": "2026-11-01"}
             for i, m in enumerate(["projection", "rotation", "projection"] * 5)]
    due = due_items(items, date(2026, 11, 12))
    assert len(due) == MAX_PER_REVIEW
    steps, groups = review_plan(due, ["rotation", "matching", "projection"])
    assert [m for m, _ in steps] == ["rotation", "projection"]
    assert sum(c for _, c in steps) == MAX_PER_REVIEW
    assert all(len(groups[m]) == c for m, c in steps)
    validate_review(items)
    with pytest.raises(ValueError):
        validate_review([{"mode": "x"}])


# ---------- продолжить тренировку ----------
def test_resume_snapshot_round_trip_and_new_training():
    from interface import game_common
    session, seed = game_common.new_training("matching", "easy", seed=42)
    source = game_common.task_source(session, factory, seed)
    first = [source.generate(session.current_level) for _ in range(3)]
    for i in range(3):
        session.record(i != 1, 4.0, ("cubes:4",))
    data = snapshot(session)
    validate_resume(data)
    assert describe(data, {"matching": "Фигуры"}) == "Фигуры, 3 из 10"
    fourth = source.generate(session.current_level)

    game_common.pending_resume = data
    again, seed2 = game_common.new_training("matching", "easy", seed=42)
    assert seed2 == 42 and [r.correct for r in again.results] == [True, False, True]
    source2 = game_common.task_source(again, factory, seed2)
    assert source2.generate(again.current_level) == fourth
    assert game_common.pending_resume is None
    assert first                                         # задания были


def test_autosave_writes_and_clears_resume(monkeypatch):
    from interface import game_common
    saved = []
    monkeypatch.setattr(prefs, "saver", lambda key, value: saved.append((key, value)))
    session, _ = game_common.new_training("rotation", "easy", seed=1)
    session.length = 2
    session.record(True, 3.0)
    assert saved[-1][0] == "resume" and saved[-1][1]["results"]
    session.record(False, 3.0)
    assert saved[-1] == ("resume", None)                 # закончена - забыть
    monkeypatch.setattr(prefs, "saver", None)
    prefs.set("resume", None)


def test_duel_and_timed_sessions_are_not_saved():
    from interface import game_common
    blitz, _ = game_common.new_training("blitz", "easy", seed=1)
    assert blitz.deadline is not None and blitz.on_record is None and blitz.no_hints
    assert blitz.length == 30


# ---------- курс ----------
def _played(index, accuracy_good):
    playlist = lesson_playlist(index)
    while not playlist.is_done:
        mode, count = playlist.current
        session = TrainingSession(mode, "easy", count)
        for k in range(count):
            session.record(accuracy_good or k == 0, 5.0)
        playlist.finish_step(session)
    return playlist


def test_course_progress_rules():
    assert [state(i, 2) for i in range(4)] == ["done", "done", "open", "locked"]
    good, bad = _played(2, True), _played(2, False)
    assert lesson_passed(good) and not lesson_passed(bad)
    assert advance(2, good) == 3 and advance(2, bad) == 2
    assert advance(5, good) == 5                         # повтор старого урока
    last = _played(len(LESSONS) - 1, True)
    assert advance(len(LESSONS) - 1, last) == len(LESSONS)
    assert lesson_playlist(0).adaptive is None and lesson_playlist(0).lesson == 0
    Preferences().set("course", 3)
    with pytest.raises(ValueError):
        Preferences().set("course", -1)


# ---------- задания для класса ----------
def test_class_assignment_and_results():
    import random
    task = make_assignment("projection", "medium", 10, random.Random(1),
                           datetime(2026, 11, 12, 9, 0))
    assert parse_code(task["code"])[:2] == ("projection", "medium")
    tasks = add_assignment([], task)
    assert limits(tasks) == {task["code"]: 10}
    with pytest.raises(ValueError):
        make_assignment("rotation", "easy", 7)

    def game(code, correct, at, points=100):
        return {"code": code, "tasks_correct": correct, "tasks_total": 10,
                "points": points, "total_seconds": 95.4, "played_at": at}
    code = task["code"]
    players = [("Аня", [game(code, 9, "2026-11-12T10:00:00"),
                        game(code, 3, "2026-11-12T09:30:00")]),
               ("Борис", [game(code, 7, "2026-11-12T10:05:00")]),
               ("Вика", [game("11-0001", 10, "2026-11-12T10:00:00")])]
    rows = results_for(code, players)
    assert [r["Игрок"] for r in rows] == ["Борис", "Аня"]      # у Ани первая попытка - 3
    assert rows[1]["Верно"] == 3 and rows[1]["Попыток"] == 2
    assert rows[0]["Время, с"] == 95


def test_class_time_limit_sets_deadline():
    from interface import game_common
    code = make_code("rotation", "easy", 123)
    game_common.class_limits = {code: 5}
    try:
        session, _ = game_common.new_training("rotation", "easy", 123, locked=True)
        assert session.deadline is not None and session.on_record is None
    finally:
        game_common.class_limits = {}


# ---------- «Что изменилось?» ----------
@pytest.mark.parametrize("level", ["easy", "medium", "hard"])
def test_changed_moves_one_visible_cube(level):
    gen = ChangedTaskGenerator(seed=4)
    for _ in range(50):
        task = gen.generate(level)
        after = set(task.after)
        assert len(after) == len(task.before) and is_connected(after)
        assert task.removed in task.before and task.added not in task.before
        assert task.added in after and task.removed not in after
        assert is_answer(task, task.added) and not is_answer(task, task.removed)


# ---------- «Взгляд наблюдателя» ----------
def test_view_from_each_side():
    towers = (Tower(-2, 1, 1, "#a"), Tower(0, -2, 2, "#b"), Tower(2, 0, 3, "#c"))
    assert [c for c, _ in view_from(towers, "front")] == ["#a", "#b", "#c"]
    assert [c for c, _ in view_from(towers, "back")] == ["#c", "#b", "#a"]
    assert [c for c, _ in view_from(towers, "right")] == ["#b", "#c", "#a"]
    assert [c for c, _ in view_from(towers, "left")] == ["#a", "#c", "#b"]


@pytest.mark.parametrize("level", ["easy", "medium", "hard"])
def test_observer_options_are_distinct_and_explained(level):
    gen = ObserverTaskGenerator(seed=6)
    for _ in range(40):
        task = gen.generate(level)
        assert len(set(task.options)) == len(task.options)
        assert task.options[task.correct_index] == view_from(task.towers, task.side)
        assert len({t.x for t in task.towers}) == len(task.towers)   # никто не загораживает
        for i in range(len(task.options)):
            if i != task.correct_index:
                assert task.explain(i)


# ---------- коды новых режимов ----------
@pytest.mark.parametrize("mode", ["changed", "observer", "blitz"])
def test_new_mode_codes(mode):
    assert parse_code(make_code(mode, "easy", 7)) == (mode, "easy", 7)


# ---------- озвучка ----------
def test_speech_respects_setting_and_passes_text_safely(monkeypatch):
    from core import speech
    started = []

    class FakeStdin:
        def write(self, data):
            started[-1]["text"] = data.decode("utf-8")

        def close(self):
            pass

    class FakeProcess:
        def __init__(self, args, **kwargs):
            started.append({"args": args})
            self.stdin = FakeStdin()

        def poll(self):
            return 0

    monkeypatch.setattr(speech.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(speech, "available", lambda: True)
    prefs.set("speech", False)
    assert speech.speak("Какая грань?") is False and not started
    text = "Какая грань окажется сверху?\"; Remove-Item C:\\ -Recurse"
    assert speech.speak(text, force=True)
    assert started[0]["text"] == text                     # текст - только через ввод
    assert all(text not in arg for arg in started[0]["args"])
    assert speech.speak("", force=True) is False
