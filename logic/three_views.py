"""Режим «Собери по трём видам»: по чертежу (вид спереди, сверху и справа)
собрать фигуру из кубиков. Без Ursina - всё проверяется автотестами.

Так читают чертежи в черчении. Важно: по трём видам фигура иногда
восстанавливается не единственным способом. Поэтому засчитывается ЛЮБАЯ
связная постройка, у которой все три вида совпадают с чертежом, - а не
только та фигура, по которой чертёж сделан.
"""

import random
from dataclasses import dataclass

from logic.construction import MAX_EXTENT, SPARE_CUBES, extent
from logic.projections import VIEWS, project
from logic.shapes import canonical, is_connected, random_shape

VIEW_ORDER = ("front", "top", "right")

THREE_VIEWS_LEVELS = {
    "easy":   {"cubes": (3, 4)},
    "medium": {"cubes": (5, 6)},
    "hard":   {"cubes": (7, 8)},
}


def views_of(cells):
    """{вид: картинка} для трёх видов чертежа."""
    return {view: project(cells, view) for view in VIEW_ORDER}


def wrong_views(build, task):
    """Какие виды постройки не совпали с чертежом (список, пустой - все совпали)."""
    if not build:
        return list(VIEW_ORDER)
    mine = views_of(build)
    return [view for view in VIEW_ORDER if mine[view] != task.views[view]]


def check_views(build, task):
    """True, если постройка связная и все три её вида совпадают с чертежом."""
    build = list(build)
    return bool(build) and is_connected(build) and not wrong_views(build, task)


def views_hint(build, task):
    """Понятная подсказка после неверной проверки."""
    build = list(build)
    if not build:
        return "Вы ещё ничего не построили."
    if not is_connected(build):
        return "Фигура распалась на части: кубики должны касаться гранями."
    names = [VIEWS[view] for view in wrong_views(build, task)]
    if len(names) == 1:
        return f"Не совпал вид {names[0]}."
    return "Не совпали виды " + " и ".join([", ".join(names[:-1]), names[-1]]) + "."


@dataclass(frozen=True)
class ThreeViewsTask:
    level: str
    shape: tuple          # фигура, по которой сделан чертёж (один из ответов)

    @property
    def views(self):
        return views_of(self.shape)

    @property
    def max_cubes(self):
        return len(self.shape) + SPARE_CUBES

    @property
    def question(self):
        return "Соберите фигуру по чертежу: виды спереди, сверху и справа"

    @property
    def tags(self):
        return (f"cubes:{len(self.shape)}",)


class ThreeViewsTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in THREE_VIEWS_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        low, high = THREE_VIEWS_LEVELS[level]["cubes"]
        while True:
            shape = random_shape(self._rng, self._rng.randint(low, high))
            key = canonical(shape)
            if extent(shape) <= MAX_EXTENT and key != self._last:
                break
        self._last = key
        return ThreeViewsTask(level, shape)
