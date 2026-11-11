import math
from time import perf_counter

from ursina import *

from core import settings
from engine.objects import ShapeView, dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import label, TopBar, UIButton
from logic.matching_tasks import MatchingTaskGenerator
from logic.answer_checker import check_answer
from logic.session import TrainingSession

LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}
LETTERS = "АБВГД"

# Камера стоит в (0, 0, -24) и смотрит прямо (см. main.py).
CAMERA_DISTANCE = 24

OPTION_SPACING_UI = 0.28     # расстояние между вариантами на экране
OPTIONS_Y_UI = -0.13         # где на экране стоят варианты
REFERENCE_Y_UI = 0.14        # где на экране стоит образец
OPTION_MAX_SIZE = 2.1        # наибольший размер варианта (единицы сцены)
REFERENCE_MAX_SIZE = 2.9

# Общий наклон всех фигур, чтобы был виден объём. Он одинаковый для образца
# и вариантов, поэтому на правильный ответ не влияет.
VIEW_ROTATION = (22, -32, 0)


def ui_to_world(ui_x, ui_y):
    """Экранная точка -> точка сцены в плоскости z = 0 (где стоят фигуры).
    Так 3D-фигура встаёт точно над своей кнопкой интерфейса.
    camera.fov - горизонтальный угол обзора, ширина экрана в единицах
    интерфейса равна window.aspect_ratio."""
    visible_width = 2 * CAMERA_DISTANCE * math.tan(math.radians(camera.fov / 2))
    units_per_ui = visible_width / window.aspect_ratio
    return ui_x * units_per_ui, ui_y * units_per_ui, 0


def fit_scale(cells, max_size):
    """Масштаб, при котором фигура не больше max_size по любой оси."""
    extent = max(max(c[i] for c in cells) - min(c[i] for c in cells) + 1
                 for i in range(3))
    return min(1.0, max_size / extent)


class MatchingGameScreen(BaseScreen):
    """Игровой экран режима 2: найти фигуру, совпадающую с образцом."""

    def __init__(self, manager, level="easy"):
        super().__init__(manager)
        self.generator = MatchingTaskGenerator()
        self.session = self._new_session(level)
        self.task = None
        self.task_started = 0.0
        self.answered = False
        self.task_objects = []    # всё, что пересоздаётся для каждого задания
        self.option_views = []
        self.option_buttons = []

        self.top_bar = self.own(TopBar("Одинаковые фигуры", self.go_back,
                                       settings.SESSION_LENGTH))
        self.own(label("Какая из фигур совпадает с образцом после поворота?",
                       (0, 0.345), 1.05, "strong", origin=(0, 0)))
        self.own(label("Образец", (0, 0.3), 0.8, "muted", origin=(0, 0)))
        self.own(label("Правая кнопка мыши - осмотреть фигуры, колесо - приблизить",
                       (window.top_left.x + 0.05, -0.455), 0.8, "muted"))

        self.feedback = self.own(label("", (0, -0.43), 1.0, origin=(0, 0)))
        self.next_button = self.own(UIButton("Дальше", self.next_task,
                                             position=(window.top_right.x - 0.15, -0.43),
                                             scale=(0.2, 0.06), variant="primary"))
        self.new_task()

    def _new_session(self, level):
        return TrainingSession("matching", level, settings.SESSION_LENGTH)

    def _clear_task_objects(self):
        for obj in self.task_objects + self.option_buttons:
            dispose(obj)
        self.task_objects = []
        self.option_views = []
        self.option_buttons = []

    def _shape(self, cells, ui_x, ui_y, max_size):
        view = ShapeView(cells, settings.SHAPE_COLOR,
                         position=ui_to_world(ui_x, ui_y),
                         rotation=VIEW_ROTATION, scale=fit_scale(cells, max_size))
        self.task_objects.append(view)
        return view

    def new_task(self):
        self.task = self.generator.generate(self.session.level)
        self.answered = False
        self.task_started = perf_counter()
        self.next_button.text = "Дальше"
        self._clear_task_objects()

        self._shape(self.task.reference, 0, REFERENCE_Y_UI, REFERENCE_MAX_SIZE)

        count = len(self.task.options)
        for index, cells in enumerate(self.task.options):
            ui_x = (index - (count - 1) / 2) * OPTION_SPACING_UI
            self.option_views.append(
                self._shape(cells, ui_x, OPTIONS_Y_UI, OPTION_MAX_SIZE))
            self.option_buttons.append(
                UIButton(LETTERS[index], lambda i=index: self.choose(i),
                         position=(ui_x, -0.33), scale=(0.12, 0.06)))

        self.feedback.text = ""
        self._update_status()

    def next_task(self):
        if not self.answered:
            return
        if self.session.is_finished:
            self.navigate("results", session=self.session)
        else:
            self.new_task()

    def choose(self, index):
        if self.answered:
            return
        self.answered = True
        seconds = perf_counter() - self.task_started
        correct = check_answer(self.task, index)
        points = self.session.record(correct, seconds)

        right = self.task.correct_index
        self.option_views[right].set_color(settings.CORRECT_COLOR)
        self.option_buttons[right].set_variant("correct")
        if correct:
            self.feedback.text = f"Верно!  +{points} баллов"
            self.feedback.color = color.hex(settings.CORRECT_COLOR)
        else:
            self.option_views[index].set_color(settings.WRONG_COLOR)
            self.option_buttons[index].set_variant("wrong")
            self.feedback.text = f"Неверно. Правильный ответ: {LETTERS[right]}"
            self.feedback.color = color.hex(settings.WRONG_COLOR)
        if self.session.is_finished:
            self.next_button.text = "Результаты"
        self._update_status()

    def _update_status(self):
        s = self.session
        self.top_bar.update_state(s.level, s.results, self.answered, s.points)

    def go_back(self):
        self.navigate("menu")

    def close(self):
        self._clear_task_objects()
        super().close()

    def input(self, key):
        if key in LEVEL_KEYS:
            self.session = self._new_session(LEVEL_KEYS[key])  # заново
            self.new_task()
