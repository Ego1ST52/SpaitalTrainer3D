"""Метки заданий и журнал заданий в базе (основа для анализа ошибок)."""

import sqlite3

import pytest

from data.database import Database
from logic.construction import ConstructionTaskGenerator
from logic.matching_tasks import MatchingTaskGenerator
from logic.projections import ProjectionTaskGenerator
from logic.session import TrainingSession
from logic.task_generator import RotationTaskGenerator


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


def test_rotation_tags_name_axes_and_moves():
    task = RotationTaskGenerator(seed=3).generate("hard")
    axes = {axis for axis, _ in task.moves}
    assert {f"axis:{a}" for a in axes} <= set(task.tags)
    assert f"moves:{len(task.moves)}" in task.tags


def test_matching_kinds_and_wrong_choice_tag():
    generator = MatchingTaskGenerator(seed=8)
    seen_mirror = False
    for _ in range(30):
        task = generator.generate("medium")
        assert task.kinds.count("correct") == 1
        assert task.kinds[task.correct_index] == "correct"
        assert task.answer_tags(task.correct_index) == ()
        if "mirror" in task.kinds:
            seen_mirror = True
            wrong = task.kinds.index("mirror")
            assert task.answer_tags(wrong) == ("chose:mirror",)
            assert "has_mirror" in task.tags
    assert seen_mirror                       # зеркальные варианты действительно бывают


def test_projection_and_construction_tags():
    task = ProjectionTaskGenerator(seed=2).generate("hard")
    assert f"view:{task.view}" in task.tags
    build = ConstructionTaskGenerator(seed=2).generate("easy")
    assert build.tags == (f"cubes:{len(build.target)}",)


def test_session_keeps_tags_per_task():
    session = TrainingSession("rotation", "easy", 2)
    session.record(True, 3, ("axis:x",))
    session.record(False, 5)
    assert session.results[0].tags == ("axis:x",) and session.results[1].tags == ()


def test_task_log_saved_with_session(db):
    user = db.create_user("Аня")
    session = TrainingSession("rotation", "medium", 3, code="12-0377")
    session.record(True, 4, ("axis:x", "moves:2"))
    session.record(False, 9, ("axis:z", "moves:3"))
    session.record(True, 2)
    db.save_session(user, session)

    log = db.get_task_log(user)
    assert [t["correct"] for t in log] == [True, False, True]
    assert log[1]["tags"] == ["axis:z", "moves:3"] and log[2]["tags"] == []
    assert all(t["mode"] == "rotation" and t["level"] == "medium" for t in log)
    assert db.get_history(user)[0]["code"] == "12-0377"


def test_deleting_player_removes_task_log(db):
    anya, boris = db.create_user("Аня"), db.create_user("Борис")
    session = TrainingSession("rotation", "easy", 1)
    session.record(True, 1, ("axis:y",))
    db.save_session(anya, session)
    db.delete_user(anya)
    assert db.get_task_log(anya) == []


def test_old_results_table_gets_code_column(tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE TABLE results (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            mode TEXT NOT NULL, level TEXT NOT NULL, played_at TEXT NOT NULL,
            tasks_total INTEGER NOT NULL, tasks_correct INTEGER NOT NULL,
            points INTEGER NOT NULL, total_seconds REAL NOT NULL);
        INSERT INTO users (name, created_at) VALUES ('Игрок', '2026-11-10T10:00:00');
        INSERT INTO results (user_id, mode, level, played_at, tasks_total, tasks_correct,
                             points, total_seconds)
            VALUES (1, 'rotation', 'easy', '2026-11-10T10:05:00', 10, 7, 100, 60);
    """)
    old.commit()
    old.close()
    database = Database(str(path))
    history = database.get_history(1)
    assert history[0]["code"] is None and history[0]["tasks_correct"] == 7
    assert database.get_task_log(1) == []                # старые тренировки без журнала
    database.close()
