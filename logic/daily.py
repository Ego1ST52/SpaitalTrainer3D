"""Задание дня: одно и то же для всех в этот день (без интернета).
Без Ursina - проверяется автотестами.

Код тренировки (logic/training_code.py) строится из даты: режим и уровень
меняются каждый день, а «зерно» генератора - из номера дня. У всех, кто
откроет задание дня сегодня, будут одинаковые задания.
"""

from datetime import date, datetime

from logic.training_code import make_code

# Режимы по кругу: каждый день - следующий
DAILY_MODES = ["rotation", "matching", "projection", "construction", "nets",
               "sections", "count", "memory", "shadow"]
# Уровень по дню недели: в начале недели проще, к выходным сложнее
WEEKDAY_LEVELS = ["easy", "easy", "medium", "medium", "medium", "hard", "hard"]


def daily_task(day=None):
    """(режим, уровень, зерно, код) задания на день day (по умолчанию сегодня)."""
    day = day or date.today()
    number = day.toordinal()
    mode = DAILY_MODES[number % len(DAILY_MODES)]
    level = WEEKDAY_LEVELS[day.weekday()]
    seed = (number * 7919) % 10000              # «перемешиваем» номер дня
    return mode, level, seed, make_code(mode, level, seed)


def daily_done(history, day=None):
    """Выполнено ли сегодняшнее задание (по коду в истории тренировок)."""
    day = day or date.today()
    code = daily_task(day)[3]
    return any(h.get("code") == code
               and datetime.fromisoformat(h["played_at"]).date() == day
               for h in history)
