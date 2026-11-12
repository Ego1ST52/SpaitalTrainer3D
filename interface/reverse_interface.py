"""Режим «Найди повороты»: два куба - «было» и «стало». Какими поворотами
получен второй? После ответа первый куб сам выполняет правильные повороты."""

import textwrap

from ursina import *

from core import settings
from core.preferences import prefs
from engine.objects import ColoredCube
from interface.choice_screen import LETTERS, ChoiceGameScreen
from interface.game_interface import make_floor
from logic.reverse_rotations import ReverseTaskGenerator, moves_text

CUBE_SCALE = 1.5
BEFORE_X = -3.6
AFTER_X = -0.9
CAPTION_SCALE = 14


class ReverseGameScreen(ChoiceGameScreen):
    MODE = "reverse"
    HINT = "Повороты - вокруг осей сцены, как в режиме «Вращение куба»"
    CARD_W = 0.6
    CARD_H = 0.07
    COLUMNS = 1
    OPTION_TEXT_SIZE = 1.05

    def make_generator(self, seed):
        return ReverseTaskGenerator(seed=seed)

    def card_positions(self, count):
        return [(self.PANEL_X, 0.12 - i * (self.CARD_H + 0.025)) for i in range(count)]

    def build_scene(self):
        skin, marks = prefs.get("cube_skin"), prefs.get("face_marks")
        scene_root = Entity()
        scene_root.floor = make_floor()
        scene_root.floor.parent = scene_root
        # «Было»: исходное положение. После ответа он повернётся сам.
        self.before = ColoredCube(skin=skin, marks=marks, scale=CUBE_SCALE,
                                  position=(BEFORE_X, 0, 0))
        # «Стало»: повороты задания складываем вложенными «шарнирами»:
        # внешний шарнир - последний поворот, внутренний - первый
        holder = Entity(parent=scene_root, position=(AFTER_X, 0, 0))
        inner = holder
        for axis, angle in reversed(self.task.moves):
            inner = Entity(parent=inner)
            setattr(inner, f"rotation_{axis}", angle * settings.AXIS_SIGN[axis])
        self.after_cube = ColoredCube(skin=skin, marks=marks, parent=inner, scale=CUBE_SCALE)
        for text, x in (("было", BEFORE_X), ("стало", AFTER_X)):
            Text(text, parent=scene_root, position=(x, 1.65, 0), billboard=True,
                 origin=(0, 0), scale=CAPTION_SCALE, color=color.hex(settings.TEXT_MUTED))
        Text("›", parent=scene_root, position=((BEFORE_X + AFTER_X) / 2, 0, 0),
             billboard=True, origin=(0, 0), scale=CAPTION_SCALE * 1.6,
             color=color.hex(self.accent))
        self.task_objects += [scene_root, self.before]

    def subtitle_text(self):
        return "Выберите цепочку: повороты выполняются слева направо"

    def option_text(self, index, option):
        return moves_text(option)

    def answer_text(self):
        reason = self.task.explain(self._chosen) or ""
        return textwrap.fill(f"Ответ {LETTERS[self.task.correct_index]}. {reason}", 52)

    def choose(self, index):
        self._chosen = index
        super().choose(index)

    def after_answer(self, correct):
        # Куб «было» выполняет правильные повороты и становится как «стало»
        if not self.before.is_empty():
            self.before.play_moves(self.task.moves)
