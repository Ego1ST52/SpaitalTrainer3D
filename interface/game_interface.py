from time import perf_counter

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.objects import ColoredCube, dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import label, Panel, TopBar, UIButton
from logic.task_generator import RotationTaskGenerator
from logic.answer_checker import check_answer
from logic.session import TrainingSession

LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}

# Название цвета -> цвет наклейки на кубе (для квадратиков на кнопках)
NAME_TO_HEX = {settings.FACE_COLOR_NAMES[face]: hex_color
               for face, (_, _, hex_color) in ColoredCube.FACES.items()}

# Правая панель с заданием
PANEL_X = 0.62
PANEL_WIDTH = 0.44
PANEL_LEFT = PANEL_X - PANEL_WIDTH / 2 + 0.03
PANEL_RIGHT = PANEL_X + PANEL_WIDTH / 2 - 0.03


def make_floor():
    """Тёмный пол с тонкой сеткой - чтобы было видно, где «низ».
    Пол без освещения (unlit): шейдер с тенями сильно осветляет тёмные
    цвета, и пол становился серым."""
    floor = Entity(model="plane", scale=14, y=-0.85, color=color.hex(settings.FLOOR_COLOR),
                   shader=unlit_shader)
    Entity(parent=floor, model=Grid(14, 14), rotation_x=90, y=0.001,
           color=color.hex(settings.ACCENT).tint(-0.55), shader=unlit_shader)
    return floor


class RotationGameScreen(BaseScreen):
    """Игровой экран режима 1: вращение куба."""

    def __init__(self, manager, level="easy"):
        super().__init__(manager)
        self.generator = RotationTaskGenerator()
        self.session = self._new_session(level)
        self.task = None
        self.task_started = 0.0
        self.answered = False
        self.playing = False       # True, пока куб показывает решение
        self.task_objects = []     # то, что пересоздаётся для каждого задания
        self.option_buttons = []

        self.own(make_floor())
        self.cube = self.own(ColoredCube(scale=1.6))   # в центре: вокруг него вращается камера

        self.top_bar = self.own(TopBar("Вращение куба", self.go_back,
                                       settings.SESSION_LENGTH))

        left = window.top_left.x + 0.05
        self.own(label("Исходное положение", (left, 0.33), 0.8, "muted"))
        self.own(label("Сверху белая грань, спереди зелёная", (left, 0.295), 1.0))
        self.own(label("Правая кнопка мыши - осмотреть куб, колесо - приблизить",
                       (left, -0.455), 0.8, "muted"))

        self.own(Panel(PANEL_WIDTH, 0.78, position=(PANEL_X, -0.06)))
        self.own(label("Повороты по порядку", (PANEL_LEFT, 0.29), 0.8, "muted"))
        self.own(label("Какая грань окажется сверху?", (PANEL_LEFT, 0.02), 1.05,
                       "strong"))
        self.feedback = self.own(label("", (PANEL_LEFT, -0.365), 0.95))

        self.own(UIButton("Показать решение", self.show_solution,
                          position=(PANEL_X - 0.105, -0.415), scale=(0.19, 0.055),
                          text_size=0.75))
        self.next_button = self.own(UIButton("Дальше", self.next_task,
                                             position=(PANEL_X + 0.105, -0.415),
                                             scale=(0.19, 0.055), variant="primary",
                                             text_size=0.8))
        self.new_task()

    def _new_session(self, level):
        return TrainingSession("rotation", level, settings.SESSION_LENGTH)

    # ---------- задания ----------
    def _clear_task_objects(self):
        for obj in self.task_objects + self.option_buttons:
            dispose(obj)
        self.task_objects = []
        self.option_buttons = []

    def new_task(self):
        self.task = self.generator.generate(self.session.level)
        self.answered = False
        self.task_started = perf_counter()
        self.cube.reset()
        self.next_button.text = "Дальше"
        self._clear_task_objects()

        for number, (axis, angle) in enumerate(self.task.moves, start=1):
            y = 0.245 - (number - 1) * 0.042
            self.task_objects.append(
                label(f"{number}.   вокруг оси {axis.upper()}", (PANEL_LEFT, y), 1.0))
            self.task_objects.append(
                label(f"{angle:+d}°", (PANEL_RIGHT, y), 1.0, "accent", origin=(0.5, 0)))

        for index, name in enumerate(self.task.options):
            button = UIButton(name.capitalize(), lambda i=index: self.choose(i),
                              position=(PANEL_X, -0.045 - index * 0.066),
                              scale=(PANEL_WIDTH - 0.06, 0.056),
                              swatch=NAME_TO_HEX.get(name))
            self.option_buttons.append(button)

        self.feedback.text = ""
        self._update_status()

    def next_task(self):
        if self.playing or not self.answered:
            return
        if self.session.is_finished:
            self.navigate("results", session=self.session)
        else:
            self.new_task()

    # ---------- ответ ----------
    def choose(self, index):
        if self.answered or self.playing:
            return
        self.answered = True
        seconds = perf_counter() - self.task_started
        correct = check_answer(self.task, index)
        points = self.session.record(correct, seconds)

        self.option_buttons[self.task.correct_index].set_variant("correct")
        if correct:
            self.feedback.text = f"Верно!  +{points} баллов"
            self.feedback.color = color.hex(settings.CORRECT_COLOR)
        else:
            self.option_buttons[index].set_variant("wrong")
            self.feedback.text = f"Неверно. Ответ: {self.task.correct_option}"
            self.feedback.color = color.hex(settings.WRONG_COLOR)
        if self.session.is_finished:
            self.next_button.text = "Результаты"
        self._update_status()

    def _update_status(self):
        s = self.session
        self.top_bar.update_state(s.level, s.results, self.answered, s.points)

    # ---------- решение ----------
    def show_solution(self):
        if not self.answered or self.playing:
            return
        self.playing = True
        self.cube.reset()
        # Повороты идут цепочкой: каждый следующий - после окончания предыдущего
        self.cube.play_moves(self.task.moves, on_done=self._solution_done)

    def _solution_done(self):
        self.playing = False

    # ---------- выход ----------
    def go_back(self):
        if self.playing or self.cube.busy:
            return  # не уходим посреди анимации
        self.navigate("menu")

    def close(self):
        self._clear_task_objects()
        super().close()

    # ---------- клавиши ----------
    def input(self, key):
        if key in LEVEL_KEYS and not self.playing:
            self.session = self._new_session(LEVEL_KEYS[key])  # заново
            self.new_task()
