"""Код тренировки: по нему другой человек получит ровно те же задания.

Генераторы заданий работают от «зерна» (seed) случайных чисел: одно и то же
зерно даёт одну и ту же последовательность заданий. Код хранит режим,
уровень и зерно, например 31-4821: режим 3 (проекции), уровень 1
(начальный), зерно 4821.
"""

import random

MODE_DIGITS = {"rotation": 1, "matching": 2, "projection": 3, "construction": 4}
LEVEL_DIGITS = {"easy": 1, "medium": 2, "hard": 3}
MAX_SEED = 9999

# В тренировке по коду число заданий фиксировано, чтобы у всех было поровну
CODE_LENGTH = {"rotation": 10, "matching": 10, "projection": 10, "construction": 5}

_MODE_BY_DIGIT = {d: m for m, d in MODE_DIGITS.items()}
_LEVEL_BY_DIGIT = {d: l for l, d in LEVEL_DIGITS.items()}


def make_code(mode, level, seed):
    if mode not in MODE_DIGITS or level not in LEVEL_DIGITS:
        raise ValueError("Неизвестный режим или уровень")
    if not 0 <= seed <= MAX_SEED:
        raise ValueError("Зерно должно быть от 0 до 9999")
    return f"{MODE_DIGITS[mode]}{LEVEL_DIGITS[level]}-{seed:04d}"


def parse_code(text):
    """'31-4821' (или '314821', с пробелами) -> ('projection', 'easy', 4821).
    Ошибка ValueError с понятным текстом, если код неверный."""
    digits = "".join(ch for ch in text if ch not in " -")
    if not digits:
        raise ValueError("Введите код тренировки.")
    if not digits.isdigit() or len(digits) != 6:
        raise ValueError("Код - это 6 цифр, например 31-4821.")
    mode = _MODE_BY_DIGIT.get(int(digits[0]))
    level = _LEVEL_BY_DIGIT.get(int(digits[1]))
    if mode is None:
        raise ValueError("Первая цифра кода - режим, от 1 до 4.")
    if level is None:
        raise ValueError("Вторая цифра кода - уровень, от 1 до 3.")
    return mode, level, int(digits[2:])


def random_seed(rng=random):
    return rng.randint(0, MAX_SEED)
