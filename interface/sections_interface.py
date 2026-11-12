"""Режим «Сечения»: какая фигура получится, если разрезать куб плоскостью."""

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.backdrop import wire_cube_mesh
from interface.choice_screen import ChoiceGameScreen
from logic.sections import SectionTaskGenerator

CUBE_SIZE = 3.0


def to_world(point):
    """Точка единичного куба (дроби от 0 до 1) -> точка сцены (куб в центре)."""
    return Vec3(*[(float(c) - 0.5) * CUBE_SIZE for c in point])


class SectionsGameScreen(ChoiceGameScreen):
    MODE = "sections"
    HINT = "Правая кнопка мыши - осмотреть куб, колесо - приблизить"
    CARD_W = 0.36
    CARD_H = 0.1
    COLUMNS = 2
    OPTION_TEXT_SIZE = 0.95

    def make_generator(self, seed):
        return SectionTaskGenerator(seed=seed)

    def build_scene(self):
        holder = Entity()
        accent = color.hex(self.accent)
        # Прозрачный куб: тонкие грани и яркие рёбра - видно всё насквозь
        Entity(parent=holder, model="cube", scale=CUBE_SIZE * 0.999, shader=unlit_shader,
               color=color.rgba(accent.r, accent.g, accent.b, 0.06))
        Entity(parent=holder, model=wire_cube_mesh(), scale=CUBE_SIZE, shader=unlit_shader,
               color=color.hex(settings.TEXT_COLOR))
        # Три точки, через которые проходит плоскость
        for point in self.task.points:
            Entity(parent=holder, model="sphere", scale=0.2, position=to_world(point),
                   color=accent, shader=unlit_shader)
        self.section = None
        self.holder = holder
        self.task_objects.append(holder)

    def subtitle_text(self):
        return "Плоскость проходит через три отмеченные точки на рёбрах"

    def option_text(self, index, option):
        return option

    def answer_text(self):
        return f"Ответ: {self.task.correct_option.lower()}"

    def after_answer(self, correct):
        # Показываем само сечение: многоугольник внутри куба
        corners = [to_world(p) for p in self.task.polygon]
        triangles = [(0, i, i + 1) for i in range(1, len(corners) - 1)]
        accent = color.hex(self.accent)
        Entity(parent=self.holder, model=Mesh(vertices=corners, triangles=triangles),
               color=color.rgba(accent.r, accent.g, accent.b, 0.55), shader=unlit_shader,
               double_sided=True)
        Entity(parent=self.holder, shader=unlit_shader, color=accent,
               model=Mesh(vertices=corners + [corners[0]], mode="line", thickness=4))
