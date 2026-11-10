"""Хранение результатов в SQLite. Без Ursina."""

import os
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    mode          TEXT NOT NULL,
    level         TEXT NOT NULL,
    played_at     TEXT NOT NULL,
    tasks_total   INTEGER NOT NULL,
    tasks_correct INTEGER NOT NULL,
    points        INTEGER NOT NULL,
    total_seconds REAL NOT NULL
);
"""


def _now():
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path):
        if path != ":memory:":
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row   # строки как словари
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    def get_or_create_user(self, name):
        name = name.strip()
        if not name:
            raise ValueError("Имя пользователя не может быть пустым")
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO users (name, created_at) VALUES (?, ?)",
                (name, _now()))
        row = self._conn.execute(
            "SELECT id FROM users WHERE name = ?", (name,)).fetchone()
        return row["id"]

    def save_session(self, user_id, session, played_at=None):
        """Сохранить итоги тренировки (TrainingSession). Возвращает id записи."""
        if session.total == 0:
            raise ValueError("Нельзя сохранить пустую тренировку")
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO results (user_id, mode, level, played_at, "
                "tasks_total, tasks_correct, points, total_seconds) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, session.mode, session.level, played_at or _now(),
                 session.total, session.correct, session.points,
                 session.total_time))
        return cursor.lastrowid

    def get_history(self, user_id, limit=None):
        """Тренировки пользователя, новые первыми (список словарей)."""
        query = ("SELECT id, mode, level, played_at, tasks_total, "
                 "tasks_correct, points, total_seconds FROM results "
                 "WHERE user_id = ? ORDER BY played_at DESC, id DESC")
        params = [user_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return [dict(row) for row in self._conn.execute(query, params)]

    def close(self):
        self._conn.close()