"""Код тренировки: по нему другой человек получит ровно те же задания.

Генераторы заданий работают от «зерна» (seed) случайных чисел: одно и то же
зерно даёт одну и ту же последовательность заданий. Код хранит режим,
уровень и зерно, например 31-4821: режим 3 (проекции), уровень 1
(начальный), зерно 4821. У режимов с номером от 10 код на цифру длиннее:
101-4821 - режим 10, уровень 1, зерно 4821.
"""

import random

MODE_DIGITS = {"rotation": 1, "matching": 2, "projection": 3, "construction": 4,
               "nets": 5, "sections": 6, "count": 7, "memory": 8, "shadow": 9,
               "reverse": 10, "symmetry": 11, "views": 12, "changed": 13, "observer": 14,
               "blitz": 15}
LEVEL_DIGITS = {"easy": 1, "medium": 2, "hard": 3}
MAX_SEED = 9999

# В тренировке по коду число заданий фиксировано, чтобы у всех было поровну
CODE_LENGTH = {"rotation": 10, "matching": 10, "projection": 10, "construction": 5,
               "nets": 10, "sections": 10, "count": 10, "memory": 5, "shadow": 10,
               "reverse": 10, "symmetry": 5, "views": 5, "changed": 10, "observer": 10,
               "blitz": 30}

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
    '101-4821' (7 цифр) - режим с двузначным номером 10."""
    return _parse_digits("".join(ch for ch in text if ch not in " -"))


def _parse_digits(digits):
    """Разбор кода без пробелов и дефиса.
    Ошибка ValueError с понятным текстом, если код неверный."""
    if not digits:
        raise ValueError("Введите код тренировки.")
    if not digits.isdigit() or len(digits) not in (6, 7):
        raise ValueError("Код - это 6 цифр, например 31-4821 (у режимов 10-15 - 7 цифр).")
    mode_part = digits[:len(digits) - 5]          # 1 или 2 цифры номера режима
    mode = _MODE_BY_DIGIT.get(int(mode_part))
    level = _LEVEL_BY_DIGIT.get(int(digits[-5]))
    if mode is None:
        raise ValueError(f"Режима с номером {int(mode_part)} нет: "
                         f"бывают от 1 до {max(MODE_DIGITS.values())}.")
    if level is None:
        raise ValueError("Цифра перед дефисом - уровень, от 1 до 3.")
    return mode, level, int(digits[-4:])


def random_seed(rng=random):
    return rng.randint(0, MAX_SEED)
