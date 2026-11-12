"""Генерация заданий «найди такую же фигуру». Без Ursina."""

import random
from dataclasses import dataclass

from logic.rotations import all_orientations, shortest_moves
from logic.shapes import (random_shape, modify_shape, mirror,
                          canonical, normalize, rotate_shape)

MATCHING_LEVELS = {
    "easy":   {"cubes": (4, 4), "options": 3},
    "medium": {"cubes": (5, 6), "options": 4},
    "hard":   {"cubes": (7, 8), "options": 5},
}

_ROTATIONS = sorted(all_orientations())

# Угол поворота по следу матрицы (сумме чисел на диагонали):
# у поворота на угол a след равен 1 + 2·cos(a)
ANGLE_BY_TRACE = {3: 0, 1: 90, 0: 120, -1: 180}


def rotation_angle(matrix):
    """На сколько градусов поворачивает матрица (0, 90, 120 или 180)."""
    return ANGLE_BY_TRACE[sum(matrix[i][i] for i in range(3))]

KIND_CAPTIONS = {"correct": "та же фигура", "mirror": "зеркальная копия",
                 "changed": "другая фигура"}
KIND_EXPLANATIONS = {
    "mirror": "Это зеркальная копия образца: её можно получить только отражением, "
              "поворотом - никогда.",
    "changed": "В этой фигуре один кубик стоит в другом месте - это другая фигура.",
}


@dataclass(frozen=True)
class MatchingTask:
    level: str
    reference: tuple      # образец
    options: tuple        # варианты (каждый - набор клеток)
    correct_index: int
    kinds: tuple = ()     # что за вариант: 'correct', 'mirror' или 'changed'

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def question(self):
        return "Какая из фигур совпадает с образцом после поворота?"

    @property
    def tags(self):
        tags = [f"cubes:{len(self.reference)}"]
        if "mirror" in self.kinds:
            tags.append("has_mirror")
        if self.options:
            tags.append(f"turn:{self.turn_angle}")    # для опыта «время против угла»
        return tuple(tags)

    def _fitting_rotations(self):
        """Повороты, которые ставят правильный вариант точно как образец."""
        target = normalize(self.reference)
        return [m for m in _ROTATIONS if rotate_shape(self.correct_option, m) == target]

    @property
    def turn_angle(self):
        """Насколько правильный вариант повёрнут относительно образца: угол
        самого маленького совмещающего поворота (0, 90, 120 или 180 градусов).
        Чем он больше, тем дольше люди обычно думают - это проверяет опыт
        на экране «Исследование»."""
        return min(rotation_angle(m) for m in self._fitting_rotations())

    @property
    def solution_moves(self):
        """Самая короткая цепочка поворотов, которая ставит правильный вариант
        точно как образец. У симметричной фигуры таких поворотов несколько
        (а может, вариант уже стоит как образец - тогда поворачивать не нужно)."""
        return min((shortest_moves(m) for m in self._fitting_rotations()), key=len)

    def option_caption(self, index):
        """Подпись под вариантом после ответа."""
        return KIND_CAPTIONS.get(self.kinds[index] if self.kinds else "", "")

    def explain(self, chosen_index):
        """Почему выбранный вариант неверен (или None для верного)."""
        if chosen_index == self.correct_index or not self.kinds:
            return None
        return KIND_EXPLANATIONS.get(self.kinds[chosen_index])

    def answer_tags(self, chosen_index):
        """Если ответ неверный - какой вариант выбрали: зеркальный или изменённый."""
        if chosen_index == self.correct_index or not self.kinds:
            return ()
        return (f"chose:{self.kinds[chosen_index]}",)


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
        mirrored = canonical(mirror(reference))
        pairs = [(correct, "correct")] + [
            (self._rotated_copy(s), "mirror" if canonical(s) == mirrored else "changed")
            for s in wrong]
        self._rng.shuffle(pairs)
        options = [cells for cells, _ in pairs]
        kinds = tuple(kind for _, kind in pairs)
        return MatchingTask(level, reference, tuple(options), kinds.index("correct"), kinds)

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