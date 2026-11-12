"""Режим «Тень»: лампа светит на фигуру с одной стороны - какая тень упадёт
на стену (или пол) напротив? Без Ursina.

Свет от лампы считаем параллельным (как от солнца), поэтому тень - это та же
проекция фигуры: так её видно, если смотреть со стороны лампы. Значит, вся
точная математика уже есть в logic/projections.py - здесь только свои
уровни, вопрос и стороны света.
"""

from dataclasses import dataclass

from logic.projections import ProjectionTask, ProjectionTaskGenerator

# Сторона лампы: (откуда светит, куда падает тень)
LIGHTS = {
    "left": ("слева", "на стене справа"),
    "right": ("справа", "на стене слева"),
    "front": ("спереди", "на стене сзади"),
    "top": ("сверху", "на полу"),
}

SHADOW_LEVELS = {
    "easy": {"cubes": (4, 4), "options": 3, "views": ("front", "top")},
    "medium": {"cubes": (5, 6), "options": 4, "views": ("front", "left", "right", "top")},
    "hard": {"cubes": (7, 8), "options": 5, "views": ("front", "left", "right", "top")},
}


@dataclass(frozen=True)
class ShadowTask(ProjectionTask):
    @property
    def question(self):
        side, target = LIGHTS[self.view]
        return f"Свет {side}. Какая тень {target}?"

    @property
    def tags(self):
        return (f"light:{self.view}", f"cubes:{len(self.shape)}")


class ShadowTaskGenerator(ProjectionTaskGenerator):
    LEVELS = SHADOW_LEVELS
    OTHER_VIEWS = tuple(LIGHTS)

    def make_task(self, *args):
        return ShadowTask(*args)
