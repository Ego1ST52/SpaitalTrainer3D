"""Режим «Сечения»: какая фигура получится, если разрезать куб плоскостью.
Без Ursina - проверяется автотестами.

Куб - единичный, от (0,0,0) до (1,1,1). Плоскость задаётся тремя точками
на рёбрах куба. Сечение - многоугольник, вершины которого - точки, где
плоскость пересекает рёбра. Всё считаем в обыкновенных дробях (Fraction),
поэтому «квадрат» и «почти квадрат» различаются точно, без погрешностей.
"""

import math
import random
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import combinations

VERTICES = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
EDGES = [(a, b) for a, b in combinations(VERTICES, 2)
         if sum(a[i] != b[i] for i in range(3)) == 1]          # 12 рёбер

SIDE_NAMES = {3: "Треугольник", 4: "Четырёхугольник", 5: "Пятиугольник",
              6: "Шестиугольник"}

SECTION_LEVELS = {
    "easy": {"steps": (0, F(1, 2), 1), "question": "sides"},
    "medium": {"steps": (0, F(1, 3), F(1, 2), F(2, 3), 1), "question": "sides"},
    "hard": {"steps": (0, F(1, 3), F(1, 2), F(2, 3), 1), "question": "shape", "options": 4},
}

# Для продвинутого уровня: похожие названия, из которых берём неверные варианты
SHAPE_FAMILIES = {
    3: ["Правильный треугольник", "Равнобедренный треугольник", "Разносторонний треугольник"],
    4: ["Квадрат", "Прямоугольник", "Ромб", "Трапеция", "Параллелограмм",
        "Четырёхугольник общего вида"],
    5: ["Пятиугольник"],
    6: ["Правильный шестиугольник", "Шестиугольник"],
}


# ---------- векторы в дробях ----------
def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def point_on_edge(edge, t):
    a, b = edge
    return tuple(F(a[i]) + (F(b[i]) - F(a[i])) * F(t) for i in range(3))


# ---------- сечение ----------
def section_polygon(p1, p2, p3):
    """Вершины сечения по порядку обхода или None, если плоскость не режет
    куб «по-настоящему» (три точки на одной прямой, плоскость совпадает
    с гранью, касается только ребра или вершины)."""
    normal = cross(sub(p2, p1), sub(p3, p1))
    if normal == (0, 0, 0):
        return None                                     # точки на одной прямой
    points = set()
    for a, b in EDGES:
        da, db = dot(normal, sub(a, p1)), dot(normal, sub(b, p1))
        if da == 0:
            points.add(tuple(F(c) for c in a))
        if db == 0:
            points.add(tuple(F(c) for c in b))
        if da * db < 0:                                 # ребро пересекает плоскость
            t = da / (da - db)
            points.add(tuple(F(a[i]) + (F(b[i]) - F(a[i])) * t for i in range(3)))
    if len(points) < 3:
        return None
    # Плоскость совпадает с гранью куба - это не сечение, а сама грань
    for i in range(3):
        if all(p[i] == 0 for p in points) or all(p[i] == 1 for p in points):
            return None
    return _order_around_center(list(points), normal)


def _order_around_center(points, normal):
    """Упорядочить вершины по кругу (углы считаем приближённо - только для
    порядка; сама фигура остаётся в точных дробях)."""
    n = [float(c) for c in normal]
    center = [sum(float(p[i]) for p in points) / len(points) for i in range(3)]
    # Два направления в плоскости сечения
    helper = [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]
    u = [helper[1] * n[2] - helper[2] * n[1], helper[2] * n[0] - helper[0] * n[2],
         helper[0] * n[1] - helper[1] * n[0]]
    v = [n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0]]

    def angle(p):
        d = [float(p[i]) - center[i] for i in range(3)]
        return math.atan2(sum(d[i] * v[i] for i in range(3)), sum(d[i] * u[i] for i in range(3)))
    return sorted(points, key=angle)


def classify(polygon):
    """Точное название фигуры: 'Квадрат', 'Правильный треугольник' и т.п."""
    n = len(polygon)
    sides = [sub(polygon[(i + 1) % n], polygon[i]) for i in range(n)]
    lengths = [dot(s, s) for s in sides]                # квадраты длин - точные дроби

    def parallel(a, b):
        return cross(a, b) == (0, 0, 0)

    if n == 3:
        if len(set(lengths)) == 1:
            return "Правильный треугольник"
        if len(set(lengths)) == 2:
            return "Равнобедренный треугольник"
        return "Разносторонний треугольник"
    if n == 4:
        pairs = parallel(sides[0], sides[2]) + parallel(sides[1], sides[3])
        right = dot(sides[0], sides[1]) == 0
        equal = len(set(lengths)) == 1
        if pairs == 2:
            if equal and right:
                return "Квадрат"
            if right:
                return "Прямоугольник"
            if equal:
                return "Ромб"
            return "Параллелограмм"
        if pairs == 1:
            return "Трапеция"
        return "Четырёхугольник общего вида"
    if n == 6:
        angles_equal = len({dot(sides[i], sides[(i + 1) % 6]) for i in range(6)}) == 1
        if len(set(lengths)) == 1 and angles_equal:
            return "Правильный шестиугольник"
        return "Шестиугольник"
    return SIDE_NAMES[n]


# ---------- задания ----------
@dataclass(frozen=True)
class SectionTask:
    level: str
    points: tuple          # три точки (x, y, z) в дробях - через них проходит плоскость
    polygon: tuple         # вершины сечения по порядку
    kind: str              # 'sides' - сколько сторон; 'shape' - точное название
    options: tuple
    correct_index: int

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def question(self):
        if self.kind == "sides":
            return "Какая фигура получится в сечении?"
        return "Назовите фигуру в сечении точно"

    @property
    def tags(self):
        return (f"sides:{len(self.polygon)}", f"type:{self.kind}")

    def answer_tags(self, chosen_index):
        return ()


class SectionTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def _random_points(self, steps):
        edges = self._rng.sample(EDGES, 3)                # три разных ребра
        return tuple(point_on_edge(e, self._rng.choice(steps)) for e in edges)

    def generate(self, level):
        if level not in SECTION_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = SECTION_LEVELS[level]
        while True:
            points = self._random_points(config["steps"])
            if len(set(points)) < 3:
                continue
            polygon = section_polygon(*points)
            if polygon is None or frozenset(polygon) == self._last:
                continue
            # Простые уровни - разнообразие: не только треугольники
            if level == "easy" and len(polygon) == 3 and self._rng.random() < 0.4:
                continue
            break
        self._last = frozenset(polygon)

        if config["question"] == "sides":
            options = list(SIDE_NAMES.values())
            correct = SIDE_NAMES[len(polygon)]
            return SectionTask(level, points, tuple(polygon), "sides", tuple(options),
                               options.index(correct))

        correct = classify(polygon)
        family = [name for name in SHAPE_FAMILIES[len(polygon)] if name != correct]
        others = [name for k, names in SHAPE_FAMILIES.items() if k != len(polygon)
                  for name in names]
        self._rng.shuffle(family)
        self._rng.shuffle(others)
        # Сначала похожие названия (той же «семьи»), потом остальные
        options = [correct] + (family + others)[:config["options"] - 1]
        self._rng.shuffle(options)
        return SectionTask(level, points, tuple(polygon), "shape", tuple(options),
                           options.index(correct))
