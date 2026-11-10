"""Начисление баллов. Без Ursina."""

LEVEL_BASE_POINTS = {"easy": 10, "medium": 20, "hard": 30}
# Через сколько секунд бонус за скорость становится нулевым
LEVEL_TIME_LIMIT = {"easy": 30, "medium": 45, "hard": 60}
MAX_SPEED_BONUS = 0.5   # бонус за мгновенный ответ: +50% к базе


def task_points(level, correct, seconds):
    """Баллы за одно задание."""
    if level not in LEVEL_BASE_POINTS:
        raise ValueError(f"Неизвестный уровень: {level!r}")
    if seconds < 0:
        raise ValueError("Время не может быть отрицательным")
    if not correct:
        return 0
    base = LEVEL_BASE_POINTS[level]
    speed = max(0.0, 1 - seconds / LEVEL_TIME_LIMIT[level])
    return base + round(base * MAX_SPEED_BONUS * speed)