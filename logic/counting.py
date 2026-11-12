"""Режим «Сколько кубиков?»: сосчитать все кубики в башне, включая
невидимые. Без Ursina - проверяется автотестами.

Фигура - это «карта высот»: в каждой клетке сетки стоит столбик из
нескольких кубиков (кубики стоят на полу и друг на друге, не висят).
Камера смотрит спереди-слева-сверху, поэтому у кубика видны три грани:
верх, перед и левый бок. Кубик скрыт, если все три закрыты соседями.
"""

import random
from dataclasses import dataclass

COUNT_LEVELS = {
    "easy": {"size": 2, "max_height": 2, "options": 3},
    "medium": {"size": 3, "max_height": 3, "options": 4},
    "hard": {"size": 3, "max_height": 4, "options": 4},
}


def total_cubes(heights):
    return sum(sum(row) for row in heights)


def cubes(heights):
    """Все кубики: (столбец x, ряд z, этаж y). Ряд z = 0 - ближний к зрителю."""
    return [(x, z, y) for z, row in enumerate(heights) for x, h in enumerate(row)
            for y in range(h)]


def is_hidden(heights, x, z, y):
    """Скрыт ли кубик: закрыт сверху, спереди (ряд ближе к зрителю)
    и слева (столбец левее) - тогда ни одна его грань не видна."""
    def height(cx, cz):
        if 0 <= cz < len(heights) and 0 <= cx < len(heights[0]):
            return heights[cz][cx]
        return 0
    covered_top = y + 1 < height(x, z)
    covered_front = y < height(x, z - 1)
    covered_left = y < height(x - 1, z)
    return covered_top and covered_front and covered_left


def hidden_count(heights):
    return sum(is_hidden(heights, x, z, y) for x, z, y in cubes(heights))


@dataclass(frozen=True)
class CountTask:
    level: str
    heights: tuple         # кортеж рядов: heights[z][x]
    options: tuple         # числа
    correct_index: int

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def question(self):
        return "Сколько всего кубиков в башне?"

    @property
    def tags(self):
        return (f"hidden:{min(hidden_count(self.heights), 3)}",
                f"grid:{len(self.heights)}")

    def answer_tags(self, chosen_index):
        if chosen_index == self.correct_index:
            return ()
        # Типичная ошибка - посчитать только видимые кубики
        visible = total_cubes(self.heights) - hidden_count(self.heights)
        if self.options[chosen_index] == visible:
            return ("chose:visible_only",)
        return ()


class CountTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in COUNT_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = COUNT_LEVELS[level]
        size = config["size"]
        while True:
            heights = tuple(tuple(self._rng.randint(0, config["max_height"])
                                  for _ in range(size)) for _ in range(size))
            # Нужны: не пустая башня и хотя бы один спрятанный кубик
            if total_cubes(heights) < 3 or hidden_count(heights) == 0:
                continue
            if heights == self._last:
                continue
            break
        self._last = heights

        correct = total_cubes(heights)
        visible = correct - hidden_count(heights)
        candidates = {visible, correct - 1, correct + 1, correct + 2, correct - 2}
        candidates = [n for n in candidates if n > 0 and n != correct]
        self._rng.shuffle(candidates)
        # «Только видимые» - самая правдоподобная ошибка, берём её всегда
        wrong = [visible] + [n for n in candidates if n != visible]
        options = [correct] + wrong[:config["options"] - 1]
        options.sort()
        return CountTask(level, heights, tuple(options), options.index(correct))
