"""Режим «Что изменилось?»: фигуру показывают несколько секунд, потом один
кубик в ней переставляют. Нужно кликнуть по переставленному кубику.
Без Ursina - проверяется автотестами.

Фигура при этом не поворачивается, поэтому сравнивать можно «как есть».
Переставленный кубик стоит на новом месте, и фигура остаётся связной.
"""

import random
from dataclasses import dataclass

from logic.shapes import NEIGHBORS, is_connected, random_shape

CHANGED_LEVELS = {
    "easy":   {"cubes": (4, 5), "show": 6},
    "medium": {"cubes": (6, 7), "show": 5},
    "hard":   {"cubes": (8, 9), "show": 4},
}


@dataclass(frozen=True)
class ChangedTask:
    level: str
    before: tuple         # фигура до изменения (клетки x, y, z)
    removed: tuple        # откуда кубик убрали
    added: tuple          # куда его поставили

    @property
    def after(self):
        cells = set(self.before)
        cells.discard(self.removed)
        cells.add(self.added)
        return tuple(sorted(cells))

    @property
    def show_seconds(self):
        return CHANGED_LEVELS[self.level]["show"]

    @property
    def question(self):
        return "Какой кубик переставили? Кликните по нему."

    @property
    def tags(self):
        return (f"cubes:{len(self.before)}",)


def is_answer(task, cell):
    """Верно ли указан переставленный кубик."""
    return tuple(cell) == task.added


class ChangedTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)

    def generate(self, level):
        if level not in CHANGED_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        low, high = CHANGED_LEVELS[level]["cubes"]
        while True:
            before = random_shape(self._rng, self._rng.randint(low, high))
            move = self._move(before)
            if move is not None:
                return ChangedTask(level, before, *move)

    def _move(self, cells):
        """(откуда, куда): убрать кубик так, чтобы остальное не распалось,
        и поставить его на новое свободное место рядом с фигурой.
        Новое место - не в «ямке» под другим кубиком: кубик должен быть виден
        хотя бы сверху или сбоку, иначе по нему нельзя кликнуть."""
        cells = list(cells)
        for _ in range(60):
            removed = self._rng.choice(cells)
            rest = [c for c in cells if c != removed]
            if not is_connected(rest):
                continue
            rest_set = set(rest)
            free = sorted({(x + dx, y + dy, z + dz) for x, y, z in rest
                           for dx, dy, dz in NEIGHBORS} - rest_set - {removed})
            free = [c for c in free if c[1] >= 0 and _visible(c, rest_set)]
            if free:
                return removed, self._rng.choice(free)
        return None


def _visible(cell, others):
    """У кубика есть хотя бы две открытые грани - его легко заметить."""
    x, y, z = cell
    open_faces = sum((x + dx, y + dy, z + dz) not in others for dx, dy, dz in NEIGHBORS)
    return open_faces >= 2
