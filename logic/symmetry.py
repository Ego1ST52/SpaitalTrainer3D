"""Режим «Симметрия»: достроить фигуру зеркально относительно плоскости.
Без Ursina - всё проверяется автотестами.

На площадке стоит половина фигуры, рядом - прозрачная «зеркальная» плоскость.
Нужно поставить кубики так, чтобы вся фигура стала симметричной.

Плоскость проходит между клетками: для плоскости X это x = -0.5, поэтому
кубик (x, y, z) отражается в (-1 - x, y, z). Половина стоит при x >= 0,
отражение - при x <= -1. Для плоскости Z всё так же, только по оси z.
"""

import random
from dataclasses import dataclass

from logic.construction import GRID_HALF, MAX_HEIGHT, Build
from logic.shapes import random_shape

SYMMETRY_LEVELS = {
    "easy":   {"cubes": (2, 3), "planes": ("x",)},
    "medium": {"cubes": (3, 4), "planes": ("x", "z")},
    "hard":   {"cubes": (5, 6), "planes": ("x", "z")},
}

PLANE_WORDS = {"x": "слева от плоскости", "z": "перед плоскостью"}
SPARE_CUBES = 3


def reflect(cell, plane):
    """Отражение клетки в плоскости 'x' (x = -0.5) или 'z' (z = -0.5)."""
    x, y, z = cell
    return (-1 - x, y, z) if plane == "x" else (x, y, -1 - z)


def mirrored_part(given, plane):
    return {reflect(cell, plane) for cell in given}


def check_symmetry(build, given, plane):
    """True, если постройка - ровно половина плюс её отражение."""
    return set(build) == set(given) | mirrored_part(given, plane)


def symmetry_diff(build, given, plane):
    """(лишние, недостающие) кубики по сравнению с правильной фигурой."""
    target = set(given) | mirrored_part(given, plane)
    build = set(build)
    return build - target, target - build


class FixedBuild(Build):
    """Постройка, в которой часть кубиков дана заранее и не убирается."""

    def __init__(self, fixed, max_cubes):
        super().__init__(max_cubes)
        self.fixed = frozenset(fixed)
        self.cells = set(self.fixed)

    def remove(self, cell):
        if cell in self.fixed:
            return False
        return super().remove(cell)

    def clear(self):
        for cell in sorted(self.cells - self.fixed):
            self.remove(cell)


@dataclass(frozen=True)
class SymmetryTask:
    level: str
    given: tuple          # половина фигуры (клетки x, y, z)
    plane: str            # 'x' или 'z'

    @property
    def target(self):
        """Вся симметричная фигура."""
        return tuple(sorted(set(self.given) | mirrored_part(self.given, self.plane)))

    @property
    def missing_count(self):
        return len(self.target) - len(self.given)

    @property
    def max_cubes(self):
        return len(self.target) + SPARE_CUBES

    @property
    def question(self):
        return (f"Достройте фигуру зеркально: поставьте {self.missing_count} "
                f"кубиков {PLANE_WORDS[self.plane]}")

    @property
    def tags(self):
        return (f"plane:{self.plane}", f"cubes:{len(self.given)}")


class SymmetryTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in SYMMETRY_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = SYMMETRY_LEVELS[level]
        while True:
            plane = self._rng.choice(config["planes"])
            shape = random_shape(self._rng, self._rng.randint(*config["cubes"]))
            given = self._place(shape, plane)
            if given is not None and given != self._last:
                break
        self._last = given
        return SymmetryTask(level, given, plane)

    @staticmethod
    def _place(shape, plane):
        """Поставить половину на площадку: вплотную к плоскости, по центру
        вдоль неё. None, если фигура не помещается."""
        across = 0 if plane == "x" else 2           # ось, перпендикулярная плоскости
        along = 2 if plane == "x" else 0
        size_across = max(c[across] for c in shape) + 1
        size_along = max(c[along] for c in shape) + 1
        height = max(c[1] for c in shape) + 1
        if size_across > GRID_HALF or size_along > 2 * GRID_HALF + 1 or height > MAX_HEIGHT:
            return None
        shift = -(size_along // 2)
        cells = []
        for cell in shape:
            moved = list(cell)
            moved[along] += shift
            cells.append(tuple(moved))
        return tuple(sorted(cells))
