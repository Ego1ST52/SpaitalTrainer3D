"""Режим «Конструирование»: собрать фигуру из кубиков по образцу.
Без Ursina - всё проверяется автотестами.

Постройка - это набор клеток (x, y, z). y = 0 - кубики, стоящие на полу.
Сравнение с образцом точное и учитывает повороты: фигуру можно собрать
в любом положении, главное - чтобы она совпадала с образцом.
"""

import random
from dataclasses import dataclass

from logic.rotations import all_orientations
from logic.shapes import apply_matrix, random_shape, canonical, is_connected, NEIGHBORS

_ROTATIONS = sorted(all_orientations())

CONSTRUCTION_LEVELS = {
    "easy":   {"cubes": (3, 4)},
    "medium": {"cubes": (5, 6)},
    "hard":   {"cubes": (7, 8)},
}

GRID_HALF = 3          # строить можно в клетках x, z от -3 до 3
MAX_HEIGHT = 6         # и по высоте от 0 до 5
SPARE_CUBES = 4        # сколько кубиков можно поставить сверх нужного
MAX_EXTENT = 5         # образец не длиннее 5 клеток по любой оси - точно влезет


def extent(cells):
    """Наибольший размер фигуры (в клетках) по осям x, y, z."""
    return max(max(c[i] for c in cells) - min(c[i] for c in cells) + 1 for i in range(3))


def check_build(build, target):
    """True, если постройка совпадает с образцом с учётом поворота.
    Пустая или рассыпанная на части постройка - не совпадает."""
    build = list(build)
    if len(build) != len(target) or not is_connected(build):
        return False
    return canonical(build) == canonical(target)


def _inside(cell):
    x, y, z = cell
    return abs(x) <= GRID_HALF and abs(z) <= GRID_HALF and 0 <= y < MAX_HEIGHT


def best_placement(build, target):
    """Как поставить образец (повернуть и сдвинуть), чтобы он как можно больше
    совпал с постройкой. Возвращает множество клеток образца на площадке.
    При равенстве лучше то положение, где образец целиком внутри площадки."""
    build = set(build)
    if not build:
        return set()
    best_key, best = None, None
    for matrix in _ROTATIONS:
        turned = [apply_matrix(matrix, cell) for cell in target]
        # Сдвиги, при которых хотя бы один кубик образца совпадает с постройкой
        shifts = {tuple(b[i] - t[i] for i in range(3)) for b in build for t in turned}
        for shift in sorted(shifts):
            placed = {tuple(t[i] + shift[i] for i in range(3)) for t in turned}
            key = (len(placed & build), all(_inside(c) for c in placed))
            if best_key is None or key > best_key:
                best_key, best = key, placed
    return best


def build_diff(build, target):
    """Чем постройка отличается от образца: (совпавшие, лишние, недостающие)
    клетки - при лучшем совмещении образца с постройкой."""
    build = set(build)
    placed = best_placement(build, target)
    return build & placed, build - placed, placed - build


def build_hint(build, target):
    """Короткая подсказка, чем постройка отличается от образца."""
    build = list(build)
    if not build:
        return "Вы ещё ничего не построили."
    if len(build) < len(target):
        return f"Не хватает кубиков: нужно {len(target)}, у вас {len(build)}."
    if len(build) > len(target):
        return f"Лишние кубики: нужно {len(target)}, у вас {len(build)}."
    if not is_connected(build):
        return "Фигура распалась на части: кубики должны касаться гранями."
    return "Кубиков столько же, но форма другая."


class Build:
    """Постройка с историей действий (для кнопки «Отменить»)."""

    def __init__(self, max_cubes):
        self.cells = set()
        self.max_cubes = max_cubes
        self._history = []          # [('add' | 'remove', клетка), ...]

    @staticmethod
    def in_bounds(cell):
        x, y, z = cell
        return abs(x) <= GRID_HALF and abs(z) <= GRID_HALF and 0 <= y < MAX_HEIGHT

    def can_add(self, cell):
        """Можно поставить кубик: место свободно, внутри площадки, лимит не
        исчерпан, и кубик стоит на полу или касается другого кубика."""
        if cell in self.cells or not self.in_bounds(cell):
            return False
        if len(self.cells) >= self.max_cubes:
            return False
        x, y, z = cell
        touches = any((x + dx, y + dy, z + dz) in self.cells for dx, dy, dz in NEIGHBORS)
        return y == 0 or touches

    def add(self, cell):
        if not self.can_add(cell):
            return False
        self.cells.add(cell)
        self._history.append(("add", cell))
        return True

    def remove(self, cell):
        if cell not in self.cells:
            return False
        self.cells.remove(cell)
        self._history.append(("remove", cell))
        return True

    def undo(self):
        """Отменить последнее действие. Возвращает True, если было что отменять."""
        if not self._history:
            return False
        action, cell = self._history.pop()
        if action == "add":
            self.cells.discard(cell)
        else:
            self.cells.add(cell)
        return True

    def clear(self):
        """Убрать все кубики (это тоже можно отменить - по одному)."""
        for cell in sorted(self.cells):
            self.remove(cell)


@dataclass(frozen=True)
class ConstructionTask:
    level: str
    target: tuple         # образец (клетки x, y, z)

    @property
    def max_cubes(self):
        return len(self.target) + SPARE_CUBES

    @property
    def question(self):
        return f"Соберите такую же фигуру из {len(self.target)} кубиков"

    @property
    def tags(self):
        return (f"cubes:{len(self.target)}",)


class ConstructionTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in CONSTRUCTION_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        low, high = CONSTRUCTION_LEVELS[level]["cubes"]
        while True:
            target = random_shape(self._rng, self._rng.randint(low, high))
            if extent(target) > MAX_EXTENT:
                continue               # слишком длинная - не влезет на площадку
            key = canonical(target)
            if key != self._last:      # не повторяем фигуру подряд
                break
        self._last = key
        return ConstructionTask(level, target)
