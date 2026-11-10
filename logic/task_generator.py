"""Генерация заданий на вращение. Без Ursina: всё проверяется тестами."""

import random
from dataclasses import dataclass

from core import settings
from logic.rotations import IDENTITY, apply_sequence, face_at

# Параметры уровней сложности
LEVELS = {
    "easy":   {"moves": (1, 1), "angles": (90, 180), "options": 3},
    "medium": {"moves": (2, 3), "angles": (90, -90, 180), "options": 4},
    "hard":   {"moves": (4, 5), "angles": (90, -90, 180), "options": 5},
}


def top_color(orientation):
    """Цвет грани, которая при этой ориентации смотрит вверх."""
    return settings.FACE_COLOR_NAMES[face_at(orientation, "+Y")]


@dataclass(frozen=True)
class RotationTask:
    level: str
    moves: tuple          # ((ось, угол), ...)
    options: tuple        # названия цветов - варианты ответа
    correct_index: int    # индекс правильного варианта

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    def describe_moves(self):
        parts = []
        for number, (axis, angle) in enumerate(self.moves, start=1):
            parts.append(f"{number}) вокруг оси {axis.upper()} на {angle:+d}°")
        return "; ".join(parts)

    @property
    def question(self):
        return ("Сейчас сверху белая грань, спереди зелёная. "
                f"Повороты: {self.describe_moves()}. "
                "Какая грань окажется сверху?")


class RotationTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last_moves = None

    def generate(self, level):
        if level not in LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = LEVELS[level]

        # Повторяем, пока не получим подходящую последовательность
        while True:
            moves = self._random_moves(config)
            if moves == self._last_moves:
                continue  # то же задание подряд не нужно
            if apply_sequence(IDENTITY, moves) == IDENTITY:
                continue  # куб вернулся в исходное положение - скучно
            break
        self._last_moves = moves

        correct = top_color(apply_sequence(IDENTITY, moves))
        options = self._build_options(moves, correct, config["options"])
        return RotationTask(level, moves, tuple(options), options.index(correct))

    def _random_moves(self, config):
        count = self._rng.randint(*config["moves"])
        moves = []
        previous_axis = None
        for _ in range(count):
            # не крутим дважды подряд вокруг одной оси
            axis = self._rng.choice([a for a in "xyz" if a != previous_axis])
            angle = self._rng.choice(config["angles"])
            moves.append((axis, angle))
            previous_axis = axis
        return tuple(moves)

    def _build_options(self, moves, correct, total):
        # Правдоподобные ошибки: перепутанный порядок и пропущенный последний поворот
        candidates = [
            top_color(apply_sequence(IDENTITY, list(reversed(moves)))),
            top_color(apply_sequence(IDENTITY, moves[:-1])),
        ]
        options = [correct]
        for color_name in candidates:
            if color_name not in options and len(options) < total:
                options.append(color_name)

        # Добираем случайными цветами, если вариантов не хватило
        others = [c for c in settings.FACE_COLOR_NAMES.values() if c not in options]
        self._rng.shuffle(others)
        options.extend(others[: total - len(options)])

        self._rng.shuffle(options)
        return options