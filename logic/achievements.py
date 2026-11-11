"""Достижения. Без Ursina: всё считается по истории тренировок (список
словарей из Database.get_history()), поэтому отдельная таблица не нужна -
достижение не может «потеряться» или разойтись с настоящими результатами.

Некоторые достижения открывают новые скины куба (см. logic/cube_skins.py).
"""

from dataclasses import dataclass

from data.statistics import accuracy_of, summarize
from logic.goals import best_streak


@dataclass(frozen=True)
class Achievement:
    key: str
    title: str
    description: str
    target: int               # сколько нужно (для полоски прогресса)
    reward_skin: str = None   # какой скин куба открывает (или None)


ACHIEVEMENTS = [
    Achievement("first_step", "Первый шаг", "Пройдите первую тренировку", 1),
    Achievement("all_faces", "Все грани", "Попробуйте все четыре режима", 4),
    Achievement("flawless", "Без ошибок", "Тренировка от 5 заданий без единой ошибки", 1,
                reward_skin="neon"),
    Achievement("rotation_master", "Мастер вращения",
                "90% и выше на продвинутом уровне во «Вращении»", 1),
    Achievement("architect", "Архитектор", "Правильно соберите 15 фигур", 15),
    Achievement("marathon", "Марафон", "Решите 100 заданий", 100, reward_skin="pastel"),
    Achievement("sharp_eye", "Острый глаз", "Точность 80% за всё время (от 50 заданий)", 1),
    Achievement("streak", "Три дня подряд", "Выполняйте цель дня 3 дня подряд", 3,
                reward_skin="jewel"),
]
BY_KEY = {a.key: a for a in ACHIEVEMENTS}
SKIN_UNLOCKS = {a.reward_skin: a.key for a in ACHIEVEMENTS if a.reward_skin}

TRAINING_MODES = ("rotation", "matching", "projection", "construction")


def progress(key, history, goal=20):
    """Насколько продвинулись: число от 0 до target (больше не бывает)."""
    target = BY_KEY[key].target
    if key == "first_step":
        value = len(history)
    elif key == "all_faces":
        value = len({h["mode"] for h in history} & set(TRAINING_MODES))
    elif key == "flawless":
        value = int(any(h["tasks_total"] >= 5 and h["tasks_correct"] == h["tasks_total"]
                        for h in history))
    elif key == "rotation_master":
        value = int(any(h["mode"] == "rotation" and h["level"] == "hard"
                        and accuracy_of(h) >= 90 for h in history))
    elif key == "architect":
        value = sum(h["tasks_correct"] for h in history if h["mode"] == "construction")
    elif key == "marathon":
        value = sum(h["tasks_total"] for h in history)
    elif key == "sharp_eye":
        stats = summarize(history)
        value = int(stats["tasks"] >= 50 and stats["accuracy"] >= 80)
    elif key == "streak":
        value = best_streak(history, goal)
    else:
        raise KeyError(f"Неизвестное достижение: {key!r}")
    return min(value, target)


def unlocked(history, goal=20):
    """Ключи полученных достижений."""
    return {a.key for a in ACHIEVEMENTS if progress(a.key, history, goal) >= a.target}


def unlocked_skins(history, goal=20):
    """Скины, открытые достижениями (обычные скины открыты всегда)."""
    done = unlocked(history, goal)
    return {skin for skin, key in SKIN_UNLOCKS.items() if key in done}


def newly_unlocked(before, after, goal=20):
    """Достижения, полученные между двумя состояниями истории (по порядку списка)."""
    gained = unlocked(after, goal) - unlocked(before, goal)
    return [a for a in ACHIEVEMENTS if a.key in gained]
