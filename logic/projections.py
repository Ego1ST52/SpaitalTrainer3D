"""Режим «Проекции»: как фигура из кубиков выглядит спереди, сверху или справа.
Без Ursina - всё проверяется автотестами.

Проекция - это «тень» фигуры на плоскость: набор закрашенных клеток
(столбец, строка). Строка 0 - низ картинки, столбец 0 - её левый край.
Сравниваем проекции точно, как множества клеток.

Оси сцены (как в Ursina): x - вправо, y - вверх, z - вглубь экрана.
Зритель изначально смотрит на фигуру со стороны -z, это и есть «спереди».
  спереди: смотрим вдоль +z, вправо = +x, вверх = +y  -> клетка (x, y)
  сверху:  смотрим вниз, ближняя к нам сторона фигуры внизу картинки,
           вправо = +x, вверх по картинке = +z           -> клетка (x, z)
  справа:  стоим справа (на +x) и смотрим на фигуру,
           вправо = +z (вглубь), вверх = +y              -> клетка (z, y)
"""

import random
from dataclasses import dataclass

from logic.shapes import random_shape, modify_shape, normalize

VIEWS = {"front": "спереди", "top": "сверху", "right": "справа"}

PROJECTION_LEVELS = {
    "easy":   {"cubes": (4, 4), "options": 3, "views": ("front", "top")},
    "medium": {"cubes": (5, 6), "options": 4, "views": ("front", "top", "right")},
    "hard":   {"cubes": (7, 8), "options": 5, "views": ("front", "top", "right")},
}


def normalize2d(points):
    """Сдвинуть картинку в угол (минимумы = 0) и отсортировать клетки."""
    points = list(points)
    min_c = min(c for c, _ in points)
    min_r = min(r for _, r in points)
    return tuple(sorted({(c - min_c, r - min_r) for c, r in points}))


def project(cells, view):
    """Проекция фигуры (набор клеток x, y, z) на плоскость вида view."""
    if view == "front":
        points = ((x, y) for x, y, z in cells)
    elif view == "top":
        points = ((x, z) for x, y, z in cells)
    elif view == "right":
        points = ((z, y) for x, y, z in cells)
    else:
        raise ValueError(f"Неизвестный вид: {view!r}")
    return normalize2d(points)


def mirror2d(picture):
    """Отразить картинку слева направо."""
    return normalize2d((-c, r) for c, r in picture)


def rotate2d(picture):
    """Повернуть картинку на 90 градусов."""
    return normalize2d((r, -c) for c, r in picture)


@dataclass(frozen=True)
class ProjectionTask:
    level: str
    shape: tuple          # фигура (клетки x, y, z)
    view: str             # 'front', 'top' или 'right'
    options: tuple        # варианты - картинки (наборы клеток столбец, строка)
    correct_index: int

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def question(self):
        return f"Как выглядит фигура {VIEWS[self.view]}?"


class ProjectionTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in PROJECTION_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = PROJECTION_LEVELS[level]

        while True:
            shape = random_shape(self._rng, self._rng.randint(*config["cubes"]))
            view = self._rng.choice(config["views"])
            if (shape, view) == self._last:
                continue   # то же задание подряд не нужно
            correct = project(shape, view)
            wrong = self._distractors(shape, view, correct, config["options"] - 1)
            if wrong is not None:
                break
        self._last = (shape, view)

        options = [correct] + wrong
        self._rng.shuffle(options)
        return ProjectionTask(level, shape, view, tuple(options), options.index(correct))

    def _distractors(self, shape, view, correct, needed):
        """Неверные, но правдоподобные картинки. Каждая точно отличается
        от правильной и от остальных. None, если набрать не удалось."""
        candidates = [project(shape, other) for other in VIEWS if other != view]
        candidates += [mirror2d(correct), rotate2d(correct),
                       rotate2d(rotate2d(correct))]
        for _ in range(10):
            changed = modify_shape(self._rng, shape)
            if changed is not None:
                candidates.append(project(normalize(changed), view))
        self._rng.shuffle(candidates)

        result = []
        for picture in candidates:
            if picture != correct and picture not in result:
                result.append(picture)
            if len(result) == needed:
                return result
        return None
