from time import perf_counter

from ursina import *

from core import settings
from engine.controls import SyncRotator
from engine.objects import ShapeView, dispose
from interface.base_screen import BaseScreen
from interface.layout3d import ui_to_world, fit_scale
from interface.ui_kit import label, TopBar, UIButton
from logic.matching_tasks import MatchingTaskGenerator
from logic.answer_checker import check_answer
from interface.hint_control import HintMixin
from interface.game_common import (LEVEL_KEYS, finish_label, finish_training, new_training,
                                     task_source)

LETTERS = "АБВГД"

OPTION_SPACING_UI = 0.28     # расстояние между вариантами на экране
OPTIONS_Y_UI = -0.13         # где на экране стоят варианты
REFERENCE_Y_UI = 0.14        # где на экране стоит образец
OPTION_MAX_SIZE = 1.7        # наибольший размер варианта (единицы сцены)
REFERENCE_MAX_SIZE = 2.4


class MatchingGameScreen(HintMixin, BaseScreen):
    """Игровой экран режима 2: найти фигуру, совпадающую с образцом.
    Ответить можно кнопкой с буквой или кликом по самой фигуре."""

    def __init__(self, manager, level="easy", seed=None, locked=False, playlist=None):
        super().__init__(manager)
        self._start(level, seed, locked, playlist)
        self.rotator = SyncRotator()
        self.task = None
        self.task_started = 0.0
        self.answered = False
        self.hovered_index = None
        self.task_objects = []    # всё, что пересоздаётся для каждого задания
        self.option_views = []
        self.option_buttons = []

        self.top_bar = self.own(TopBar("matching", self.go_back))
        self.own(label("Какая из фигур совпадает с образцом после поворота?",
                       (0, 0.345), 1.05, "strong", origin=(0, 0)))
        self.own(label("Образец", (0, 0.3), 0.8, "muted", origin=(0, 0)))
        self.own(label("Правая кнопка мыши - повернуть все фигуры сразу  •  "
                       "R - исходный вид  •  клик по фигуре - ответ",
                       (window.top_left.x + 0.05, -0.455), 0.8, "muted"))

        self.feedback = self.own(label("", (0, -0.415), 1.0, origin=(0, 0)))
        self.next_button = self.own(UIButton("Дальше", self.next_task,
                                             position=(window.top_right.x - 0.15, -0.43),
                                             scale=(0.2, 0.06), variant="primary"))
        # После ответа: правильная фигура поворачивается и встаёт как образец
        self.solve_button = self.own(UIButton("Совместить с образцом", self.show_solution,
                                              position=(window.top_right.x - 0.15, -0.355),
                                              scale=(0.2, 0.05), text_size=0.7))
        self.solve_button.enabled = False
        self.playing = False
        # До ответа на месте кнопки «Совместить» - подсказка
        self.setup_hint((window.top_right.x - 0.15, -0.355), scale=(0.2, 0.05), text_size=0.7)
        self.new_task()

    def _start(self, level, seed=None, locked=False, playlist=None):
        """Новая тренировка: свой код и генератор заданий с этим зерном."""
        self.playlist = playlist     # шаг «Моей тренировки» или None
        self.session, seed = new_training("matching", level, seed, locked, playlist)
        self.generator = task_source(self.session, lambda s: MatchingTaskGenerator(seed=s),
                                     seed)

    def _clear_task_objects(self):
        for obj in self.task_objects + self.option_buttons:
            dispose(obj)
        self.task_objects = []
        self.option_views = []
        self.option_buttons = []

    def _shape(self, cells, ui_x, ui_y, max_size, clickable):
        view = ShapeView(cells, settings.SHAPE_COLOR, clickable=clickable,
                         position=ui_to_world(ui_x, ui_y),
                         scale=fit_scale(cells, max_size))
        self.task_objects.append(view)
        return view

    def new_task(self):
        self.task = self.generator.generate(self.session.current_level)
        self.answered = False
        self.playing = False
        self.solve_button.enabled = False
        self.hovered_index = None
        self.task_started = perf_counter()
        self.next_button.text = "Дальше"
        self._clear_task_objects()

        reference = self._shape(self.task.reference, 0, REFERENCE_Y_UI,
                                REFERENCE_MAX_SIZE, clickable=False)

        count = len(self.task.options)
        for index, cells in enumerate(self.task.options):
            ui_x = (index - (count - 1) / 2) * OPTION_SPACING_UI
            self.option_views.append(
                self._shape(cells, ui_x, OPTIONS_Y_UI, OPTION_MAX_SIZE, clickable=True))
            self.option_buttons.append(
                UIButton(LETTERS[index], lambda i=index: self.choose(i),
                         position=(ui_x, -0.33), scale=(0.12, 0.06)))

        # Каждая фигура вращается вокруг своего центра, все - одинаково
        self.rotator.set_targets([reference] + self.option_views)
        self.rotator.reset()
        self.feedback.text = ""
        self.reset_hint()
        self._update_status()

    def next_task(self):
        if not self.answered or self.playing:
            return
        if self.session.is_finished:
            finish_training(self)
        else:
            self.new_task()

    def choose(self, index):
        if self.answered or self.hint_blocked(index):
            return
        self.answered = True
        self.close_hint()
        seconds = perf_counter() - self.task_started
        correct = check_answer(self.task, index)
        points = self.session.record(correct, seconds,
                                     self.task.tags + self.task.answer_tags(index),
                                     hints=self.hints_used)
        self.top_bar.flash_level(self.session)   # «Уровень повышен» и т.п.

        right = self.task.correct_index
        for view in self.option_views:
            view.set_color(settings.SHAPE_COLOR)      # снимаем подсветку наведения
        self.option_views[right].set_color(settings.CORRECT_COLOR)
        self.option_buttons[right].set_variant("correct")
        if correct:
            self.feedback.text = f"Верно!  +{points} баллов"
            self.feedback.color = color.hex(settings.CORRECT_COLOR)
        else:
            self.option_views[index].set_color(settings.WRONG_COLOR)
            self.option_buttons[index].set_variant("wrong")
            self.feedback.text = (f"Неверно, ответ {LETTERS[right]}.  "
                                  f"{self.task.explain(index) or ''}").strip()
            self.feedback.color = color.hex(settings.WRONG_COLOR)
        # Подписи под вариантами: что это за фигура на самом деле
        for i, button in enumerate(self.option_buttons):
            self.task_objects.append(label(self.task.option_caption(i),
                                           (button.x, -0.378), 0.72, "muted", origin=(0, 0)))
        self.solve_button.enabled = bool(self.task.solution_moves)
        if self.session.is_finished:
            self.next_button.text = finish_label(self)
        self._update_status()

    def on_option_removed(self, index):
        self.option_views[index].set_color(settings.TEXT_MUTED)

    def show_solution(self):
        """Правильный вариант поворачивается по шагам и встаёт как образец."""
        if not self.answered or self.playing:
            return
        self.playing = True
        self.solve_button.enabled = False
        self.rotator.reset()                 # все фигуры - в одном ракурсе
        self.option_views[self.task.correct_index].play_moves(
            self.task.solution_moves, on_done=self._solution_done)

    def _solution_done(self):
        self.playing = False
        self.feedback.text = "Теперь правильная фигура стоит точно как образец"
        self.feedback.color = color.hex(settings.CORRECT_COLOR)

    def _update_status(self):
        self.top_bar.update_state(self.session, self.answered)

    def _option_under_mouse(self):
        """Номер варианта, над которым курсор, или None."""
        for index, view in enumerate(self.option_views):
            if view.contains(mouse.hovered_entity):
                return index
        return None

    def update(self):
        self.rotator.update()
        if self.answered:
            return
        index = self._option_under_mouse()
        if index != self.hovered_index:
            for i, view in enumerate(self.option_views):
                if i in self.removed_options:
                    view.set_color(settings.TEXT_MUTED)       # вычеркнут подсказкой
                else:
                    view.set_color(settings.SHAPE_HOVER if i == index else settings.SHAPE_COLOR)
            self.hovered_index = index

    def go_back(self):
        if self.playing:
            return                            # не уходим посреди анимации
        self.navigate("menu")

    def close(self):
        self._clear_task_objects()
        super().close()

    def input(self, key):
        if key in LEVEL_KEYS and not self.session.locked:
            self._start(LEVEL_KEYS[key])  # заново, с новым кодом
            self.new_task()
        elif key == "r":
            self.rotator.reset()
        elif key == "h":
            self.use_hint()
        elif key == "left mouse down":
            index = self._option_under_mouse()
            if index is not None:
                self.choose(index)
