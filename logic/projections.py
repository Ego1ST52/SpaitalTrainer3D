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


KIND_EXPLANATIONS = {
    "mirror": "Сторона верная, но картинка отражена слева направо.",
    "rotated": "Сторона верная, но картинка повёрнута.",
    "changed": "Так выглядела бы другая фигура: один кубик в ней переставлен.",
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
    elif view == "left":      # стоим слева (на -x), вправо = -z
        points = ((-z, y) for x, y, z in cells)
    elif view == "back":      # стоим сзади (на +z), вправо = -x
        points = ((-x, y) for x, y, z in cells)
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
    # Откуда взялся каждый вариант: 'correct', 'view:top' (вид с другой стороны),
    # 'mirror' (отражён), 'rotated' (повёрнут) или 'changed' (другая фигура)
    kinds: tuple = ()

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def tags(self):
        return (f"view:{self.view}", f"cubes:{len(self.shape)}")

    def _kind(self, index):
        return self.kinds[index] if self.kinds else ""

    def answer_tags(self, chosen_index):
        """Типичная ошибка, которую выдаёт выбранный неверный вариант."""
        kind = self._kind(chosen_index)
        if kind.startswith("view:"):
            return ("chose:other_view",)
        if kind in ("mirror", "rotated"):
            return (f"chose:{kind}_view",)      # не путать с «зеркальной фигурой»
        return ()

    def explain(self, chosen_index):
        """Почему выбранная картинка неверна (None - верна или объяснить нечем)."""
        kind = self._kind(chosen_index)
        if kind.startswith("view:"):
            other = kind[5:]
            return f"Это вид {VIEWS.get(other, other)}, а нужен вид {VIEWS[self.view]}."
        return KIND_EXPLANATIONS.get(kind)

    @property
    def question(self):
        return f"Как выглядит фигура {VIEWS[self.view]}?"


class ProjectionTaskGenerator:
    # Наследник (режим «Тень») подставляет свои уровни, виды и класс задания
    LEVELS = PROJECTION_LEVELS
    OTHER_VIEWS = tuple(VIEWS)            # из каких видов брать неверные варианты

    def make_task(self, *args):
        return ProjectionTask(*args)

    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in self.LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = self.LEVELS[level]

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

        pairs = [(correct, "correct")] + wrong
        self._rng.shuffle(pairs)
        options = tuple(picture for picture, _ in pairs)
        kinds = tuple(kind for _, kind in pairs)
        return self.make_task(level, shape, view, options, kinds.index("correct"), kinds)

    def _distractors(self, shape, view, correct, needed):
        """Неверные, но правдоподобные картинки [(картинка, откуда взялась)].
        Каждая точно отличается от правильной и от остальных.
        None, если набрать не удалось."""
        candidates = [(project(shape, other), f"view:{other}")
                      for other in self.OTHER_VIEWS if other != view]
        candidates += [(mirror2d(correct), "mirror"), (rotate2d(correct), "rotated"),
                       (rotate2d(rotate2d(correct)), "rotated")]
        for _ in range(10):
            changed = modify_shape(self._rng, shape)
            if changed is not None:
                candidates.append((project(normalize(changed), view), "changed"))
        self._rng.shuffle(candidates)

        result = []
        pictures = {correct}
        for picture, kind in candidates:
            if picture not in pictures:
                pictures.add(picture)
                result.append((picture, kind))
            if len(result) == needed:
                return result
        return None
