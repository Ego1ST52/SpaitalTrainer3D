import sqlite3
import pytest

from data.database import Database
from data.statistics import summarize
from logic.session import TrainingSession


def make_session(mode="rotation", level="easy", answers=((True, 0), (False, 10), (True, 30))):
    session = TrainingSession(mode, level, length=len(answers))
    for correct, seconds in answers:
        session.record(correct, seconds)
    return session


@pytest.fixture
def db():
    database = Database(":memory:")
    yield database
    database.close()


def test_get_or_create_user_is_idempotent(db):
    first = db.get_or_create_user("Аня")
    assert db.get_or_create_user("Аня") == first
    assert db.get_or_create_user("Борис") != first


def test_blank_user_name_rejected(db):
    with pytest.raises(ValueError):
        db.get_or_create_user("   ")


def test_save_and_read_back(db):
    user = db.get_or_create_user("Аня")
    db.save_session(user, make_session())          # баллы: 15 + 0 + 10 = 25
    row = db.get_history(user)[0]
    assert row["mode"] == "rotation" and row["level"] == "easy"
    assert row["tasks_total"] == 3 and row["tasks_correct"] == 2
    assert row["points"] == 25
    assert row["total_seconds"] == 40


def test_history_is_newest_first_and_limited(db):
    user = db.get_or_create_user("Аня")
    db.save_session(user, make_session(), played_at="2026-11-01T10:00:00")
    db.save_session(user, make_session(), played_at="2026-11-03T10:00:00")
    db.save_session(user, make_session(), played_at="2026-11-02T10:00:00")
    dates = [r["played_at"] for r in db.get_history(user)]
    assert dates == ["2026-11-03T10:00:00", "2026-11-02T10:00:00",
                     "2026-11-01T10:00:00"]
    assert len(db.get_history(user, limit=2)) == 2


def test_history_is_separate_per_user(db):
    anna = db.get_or_create_user("Аня")
    boris = db.get_or_create_user("Борис")
    db.save_session(anna, make_session())
    assert len(db.get_history(anna)) == 1
    assert db.get_history(boris) == []


def test_unknown_user_rejected(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.save_session(999, make_session())


def test_empty_session_rejected(db):
    user = db.get_or_create_user("Аня")
    with pytest.raises(ValueError):
        db.save_session(user, TrainingSession("rotation", "easy"))


def test_data_survives_reopening_file(tmp_path):
    path = str(tmp_path / "sub" / "test.db")   # папка sub создаётся сама
    first = Database(path)
    user = first.get_or_create_user("Аня")
    first.save_session(user, make_session())
    first.close()

    second = Database(path)
    assert second.get_or_create_user("Аня") == user
    assert len(second.get_history(user)) == 1
    second.close()


def test_summarize_empty():
    summary = summarize([])
    assert summary["sessions"] == 0 and summary["accuracy"] == 0.0
    assert summary["best_points"] == 0


def test_summarize_values():
    history = [
        {"tasks_total": 10, "tasks_correct": 8, "points": 120, "total_seconds": 100},
        {"tasks_total": 10, "tasks_correct": 6, "points": 80, "total_seconds": 200},
    ]
    summary = summarize(history)
    assert summary["sessions"] == 2 and summary["tasks"] == 20
    assert summary["correct"] == 14
    assert summary["accuracy"] == pytest.approx(70)
    assert summary["points"] == 200 and summary["best_points"] == 120
    assert summary["average_seconds"] == pytest.approx(15)