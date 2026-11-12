"""Режим «Развёртка»: из плоской развёртки складывается куб."""

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.net_fold import NetFold
from interface.choice_screen import ChoiceGameScreen
from interface.ui_kit import FRONT, label
from logic.nets import NetTaskGenerator

NET_POSITION = Vec3(-2.4, 0.3, 0.3)   # где лежит развёртка в сцене
NET_CELL = 0.85                       # размер клетки


def iso_cube(parent, letters, size, colors):
    """Маленький изометрический кубик: видны верхняя, передняя (слева)
    и правая грани, на каждой - буква. letters = (сверху, спереди, справа)."""
    r = size / 2
    w = r * 0.866                      # cos(30°)
    top, center, bottom = Vec3(0, r, 0), Vec3(0, 0, 0), Vec3(0, -r, 0)
    up_left, up_right = Vec3(-w, r / 2, 0), Vec3(w, r / 2, 0)
    low_left, low_right = Vec3(-w, -r / 2, 0), Vec3(w, -r / 2, 0)
    faces = [
        ((top, up_right, center, up_left), colors[0], Vec3(0, r / 2, 0)),
        ((up_left, center, bottom, low_left), colors[1], Vec3(-w / 2, -r / 4, 0)),
        ((center, up_right, low_right, bottom), colors[2], Vec3(w / 2, -r / 4, 0)),
    ]
    for (corners, hex_color, middle), letter in zip(faces, letters):
        Entity(parent=parent, shader=unlit_shader, double_sided=True, z=FRONT,
               model=Mesh(vertices=list(corners), triangles=[(0, 1, 2), (0, 2, 3)]),
               color=color.hex(hex_color))
        text = label(letter, (middle.x, middle.y), size * 14, "#0b1220" if hex_color ==
                     colors[0] else "strong", origin=(0, 0), parent=parent)
        text.z = FRONT * 2


class NetsGameScreen(ChoiceGameScreen):
    MODE = "nets"
    HINT = "После ответа развёртка сложится в кубик - посмотрите, как это получается"

    def make_generator(self, seed):
        return NetTaskGenerator(seed=seed)

    def build_scene(self):
        self.net = NetFold(self.task.cells, self.task.letters,
                           marked=self.task.marked if self.task.kind == "opposite" else None,
                           accent=self.accent, cell=NET_CELL, position=NET_POSITION)
        self.task_objects.append(self.net)

    def subtitle_text(self):
        if self.task.kind == "opposite":
            return "Мысленно сложите развёртку в кубик"
        return "На кубике видны верхняя, передняя и правая грани"

    def option_text(self, index, option):
        return option if self.task.kind == "opposite" else None

    def draw_option(self, index, option, card):
        iso_cube(card, option, 0.13, (self.accent, settings.SURFACE_HOVER, settings.BUTTON_COLOR))

    def answer_text(self):
        if self.task.kind == "opposite":
            marked = self.task.letters[self.task.marked]
            return f"Напротив «{marked}» - «{self.task.correct_option}»"
        return super().answer_text()

    def after_answer(self, correct):
        # Показываем решение: развёртка складывается в кубик
        self.net.fold()

    def update(self):
        # Сложенный кубик медленно вращается, чтобы были видны все грани
        if self.answered and self.net.is_folded:
            self.net.rotation_y += 30 * time.dt
