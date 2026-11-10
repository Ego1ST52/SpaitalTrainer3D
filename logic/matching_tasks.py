"""Генерация заданий «найди такую же фигуру». Без Ursina."""

import random
from dataclasses import dataclass

from logic.rotations import all_orientations
from logic.shapes import (random_shape, modify_shape, mirror,
                          canonical, rotate_shape)

MATCHING_LEVELS = {
    "easy":   {"cubes": (4, 4), "options": 3},
    "medium": {"cubes": (5, 6), "options": 4},
    "hard":   {"cubes": (7, 8), "options": 5},
}

_ROTATIONS = sorted(all_orientations())


@dataclass(frozen=True)
class MatchingTask:
    level: str
    reference: tuple      # образец
    options: tuple        # варианты (каждый - набор клеток)
    correct_index: int

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def question(self):
        return "Какая из фигур совпадает с образцом после поворота?"


class MatchingTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in MATCHING_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = MATCHING_LEVELS[level]

        while True:
            count = self._rng.randint(*config["cubes"])
            reference = random_shape(self._rng, count)
            key = canonical(reference)
            if key == self._last:
                continue  # не повторяем фигуру подряд
            wrong = self._distractors(reference, config["options"] - 1)
            if wrong is None:
                continue
            break
        self._last = key

        correct = self._rotated_copy(reference)
        options = [correct] + [self._rotated_copy(s) for s in wrong]
        self._rng.shuffle(options)
        return MatchingTask(level, reference, tuple(options),
                            options.index(correct))

    def _distractors(self, reference, needed):
        """Неправильные варианты: зеркало (если оно отличается) и перестановки."""
        used = {canonical(reference)}
        result = []
        mirrored = mirror(reference)
        if canonical(mirrored) not in used:
            used.add(canonical(mirrored))
            result.append(mirrored)

        attempts = 0
        while len(result) < needed and attempts < 100:
            attempts += 1
            base = self._rng.choice([reference] + result)
            candidate = modify_shape(self._rng, base)
            if candidate is None or canonical(candidate) in used:
                continue
            used.add(canonical(candidate))
            result.append(candidate)

        return result[:needed] if len(result) >= needed else None

    def _rotated_copy(self, cells):
        return rotate_shape(cells, self._rng.choice(_ROTATIONS))