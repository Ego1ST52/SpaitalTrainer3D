"""Хранение результатов в SQLite. Без Ursina."""

import json
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

-- Личные настройки игрока: ключ -> значение (в виде JSON)
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER NOT NULL REFERENCES users(id),
    key     TEXT NOT NULL,
    value   TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
);

-- Журнал заданий: каждое задание отдельно (для анализа ошибок и отчёта)
CREATE TABLE IF NOT EXISTS task_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL REFERENCES results(id),
    user_id   INTEGER NOT NULL REFERENCES users(id),
    mode      TEXT NOT NULL,
    level     TEXT NOT NULL,
    correct   INTEGER NOT NULL,
    seconds   REAL NOT NULL,
    tags      TEXT NOT NULL            -- метки через запятую: 'axis:x,moves:2'
);

-- Состояние приложения, например, кто играл последним
CREATE TABLE IF NOT EXISTS app_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Цвета аватаров игроков - по очереди для каждого нового игрока
AVATAR_COLORS = ["#22d3ee", "#a78bfa", "#fbbf24", "#34d399", "#f472b6",
                 "#60a5fa", "#fb923c", "#f87171"]


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
        self._migrate()

    def _migrate(self):
        """Обновить базу, созданную старой версией программы: добавить колонку
        с цветом аватара. Старые данные при этом сохраняются."""
        columns = [row["name"] for row in self._conn.execute("PRAGMA table_info(users)")]
        if "color" not in columns:
            with self._conn:
                self._conn.execute("ALTER TABLE users ADD COLUMN color TEXT")
        # Код тренировки в результатах (для «задания дня»)
        columns = [row["name"] for row in self._conn.execute("PRAGMA table_info(results)")]
        if "code" not in columns:
            with self._conn:
                self._conn.execute("ALTER TABLE results ADD COLUMN code TEXT")

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

    # ---------- игроки ----------
    @staticmethod
    def _clean_name(name):
        """Имя без лишних пробелов. Ошибка ValueError, если оно пустое или длинное."""
        name = name.strip()
        if not name:
            raise ValueError("Введите имя игрока.")
        if len(name) > 20:
            raise ValueError("Имя слишком длинное (до 20 букв).")
        return name

    def create_user(self, name):
        """Новый игрок. Ошибка ValueError, если имя пустое или уже занято."""
        name = self._clean_name(name)
        count = self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        color = AVATAR_COLORS[count % len(AVATAR_COLORS)]
        try:
            with self._conn:
                cursor = self._conn.execute(
                    "INSERT INTO users (name, created_at, color) VALUES (?, ?, ?)",
                    (name, _now(), color))
        except sqlite3.IntegrityError:
            raise ValueError("Игрок с таким именем уже есть.") from None
        return cursor.lastrowid

    def rename_user(self, user_id, name):
        """Переименовать игрока. Ошибка ValueError, если имя неверное или занято."""
        name = self._clean_name(name)
        try:
            with self._conn:
                cursor = self._conn.execute("UPDATE users SET name = ? WHERE id = ?",
                                            (name, user_id))
        except sqlite3.IntegrityError:
            raise ValueError("Игрок с таким именем уже есть.") from None
        if cursor.rowcount == 0:
            raise ValueError("Такого игрока нет.")

    def delete_user(self, user_id):
        """Удалить игрока вместе с его тренировками и настройками.
        Единственного игрока удалить нельзя - статистику вести будет не за кем."""
        count = self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count <= 1:
            raise ValueError("Нельзя удалить единственного игрока.")
        with self._conn:      # всё или ничего: одна транзакция
            self._conn.execute("DELETE FROM task_log WHERE user_id = ?", (user_id,))
            self._conn.execute("DELETE FROM results WHERE user_id = ?", (user_id,))
            self._conn.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
            cursor = self._conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if cursor.rowcount == 0:
            raise ValueError("Такого игрока нет.")
        if self.get_state("last_user") == user_id:
            with self._conn:
                self._conn.execute("DELETE FROM app_state WHERE key = 'last_user'")

    def list_users(self):
        """Все игроки с числом тренировок (по порядку создания)."""
        rows = self._conn.execute(
            "SELECT u.id, u.name, u.color, COUNT(r.id) AS sessions "
            "FROM users u LEFT JOIN results r ON r.user_id = u.id "
            "GROUP BY u.id ORDER BY u.id")
        users = []
        for i, row in enumerate(rows):
            user = dict(row)
            # у игроков из старой базы цвета ещё нет - даём по порядку
            user["color"] = user["color"] or AVATAR_COLORS[i % len(AVATAR_COLORS)]
            users.append(user)
        return users

    # ---------- настройки игрока ----------
    def get_settings(self, user_id):
        """Настройки игрока словарём. Испорченные записи пропускаются."""
        result = {}
        for row in self._conn.execute(
                "SELECT key, value FROM settings WHERE user_id = ?", (user_id,)):
            try:
                result[row["key"]] = json.loads(row["value"])
            except ValueError:
                pass
        return result

    def set_setting(self, user_id, key, value):
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)",
                (user_id, key, json.dumps(value)))

    # ---------- состояние приложения ----------
    def get_state(self, key, default=None):
        row = self._conn.execute("SELECT value FROM app_state WHERE key = ?",
                                 (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_state(self, key, value):
        with self._conn:
            self._conn.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                               (key, json.dumps(value)))

    # ---------- результаты ----------
    def save_session(self, user_id, session, played_at=None):
        """Сохранить итоги тренировки (TrainingSession). Возвращает id записи."""
        if session.total == 0:
            raise ValueError("Нельзя сохранить пустую тренировку")
        with self._conn:      # итог и все задания - одной транзакцией
            cursor = self._conn.execute(
                "INSERT INTO results (user_id, mode, level, played_at, "
                "tasks_total, tasks_correct, points, total_seconds, code) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, session.mode, session.summary_level, played_at or _now(),
                 session.total, session.correct, session.points,
                 session.total_time, getattr(session, "code", None)))
            result_id = cursor.lastrowid
            self._conn.executemany(
                "INSERT INTO task_log (result_id, user_id, mode, level, correct, seconds, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(result_id, user_id, session.mode, r.level or session.level, int(r.correct),
                  r.seconds, ",".join(r.tags)) for r in session.results])
        return result_id

    def get_task_log(self, user_id):
        """Все задания игрока: словари с mode, level, correct, seconds, tags (список)."""
        rows = self._conn.execute(
            "SELECT t.mode, t.level, t.correct, t.seconds, t.tags, r.played_at "
            "FROM task_log t JOIN results r ON r.id = t.result_id "
            "WHERE t.user_id = ? ORDER BY t.id", (user_id,))
        return [{"mode": row["mode"], "level": row["level"], "correct": bool(row["correct"]),
                 "seconds": row["seconds"], "played_at": row["played_at"],
                 "tags": [t for t in row["tags"].split(",") if t]} for row in rows]

    def get_history(self, user_id, limit=None):
        """Тренировки пользователя, новые первыми (список словарей)."""
        query = ("SELECT id, mode, level, played_at, tasks_total, "
                 "tasks_correct, points, total_seconds, code FROM results "
                 "WHERE user_id = ? ORDER BY played_at DESC, id DESC")
        params = [user_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return [dict(row) for row in self._conn.execute(query, params)]

    def close(self):
        self._conn.close()