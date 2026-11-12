"""«Блиц»: за 60 секунд решить как можно больше заданий «Вращения куба».
После ответа следующее задание появляется само. Время показывает таймер
в верхней панели (TopBar); когда оно выходит - итоги."""

from ursina import *

from core.preferences import prefs
from engine.objects import ColoredCube
from interface.choice_screen import ChoiceGameScreen
from interface.game_common import finish_training
from interface.game_interface import make_floor
from logic.cube_skins import face_names, option_text, start_description
from logic.reverse_rotations import moves_text
from logic.task_generator import RotationTaskGenerator

NEXT_DELAY = 0.45             # пауза после ответа, секунд
CUBE_POSITION = Vec3(-2.3, 0, 0)


class BlitzGameScreen(ChoiceGameScreen):
    MODE = "blitz"
    HINT = "Отвечайте быстро: следующее задание появится само"
    CARD_H = 0.12
    OPTION_TEXT_SIZE = 1.2

    def make_generator(self, seed):
        return RotationTaskGenerator(seed=seed, face_names=face_names(prefs.get("cube_skin")))

    def build_scene(self):
        skin = prefs.get("cube_skin")
        root = Entity()
        make_floor().parent = root
        ColoredCube(skin=skin, marks=prefs.get("face_marks"), scale=1.6, parent=root,
                    position=CUBE_POSITION)
        self.task_objects.append(root)

    def subtitle_text(self):
        skin = prefs.get("cube_skin")
        return f"{start_description(skin)}.  Повороты: {moves_text(self.task.moves)}"

    def option_text(self, index, option):
        return option_text(prefs.get("cube_skin"), option)

    def new_task(self):
        super().new_task()
        self.question.text = f"Какая грань окажется {self.task.target_word}?"

    def after_answer(self, correct):
        invoke(self._auto_next, delay=NEXT_DELAY)

    def _auto_next(self):
        if self.is_empty() or not self.answered or getattr(self.session, "timed_out", False):
            return
        if self.session.is_finished:
            finish_training(self)
        else:
            self.new_task()
