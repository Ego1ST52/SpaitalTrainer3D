import textwrap
from time import perf_counter

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.controls import SyncRotator
from engine.objects import ShapeView, dispose
from interface.base_screen import BaseScreen
from interface.layout3d import ui_to_world, fit_scale
from interface.ui_kit import FRONT, label, mode_color, Panel, TopBar, UIButton
from logic.answer_checker import check_answer
from logic.projections import ProjectionTaskGenerator, VIEWS
from interface.hint_control import HintMixin
from interface.game_common import (LEVEL_KEYS, finish_label, finish_training, new_training,
                                     task_source)

LETTERS = "АБВГД"

SHAPE_UI = (-0.42, -0.02)    # где на экране стоит фигура
SHAPE_MAX_SIZE = 4.0         # наибольший размер фигуры (единицы сцены)
PANEL_X = 0.42               # центр правой панели с вариантами
CARD_SIZE = 0.2
CARD_STEP = 0.24
VIEW_LABEL_SCALE = 14        # размер подписей сторон в 3D-сцене
# Поворот фигуры (наклон, разворот), при котором видна ровно эта сторона.
# Проверено тестом: силуэт кубиков на экране совпадает с проекцией из logic.
VIEW_ROTATIONS = {"front": (0, 0), "top": (-90, 0), "right": (0, 90)}
TURN_SECONDS = 0.8


class ProjectionGameScreen(HintMixin, BaseScreen):
    """Режим «Проекции»: выбрать, как фигура выглядит спереди, сверху или справа."""

    def __init__(self, manager, level="easy", seed=None, locked=False, playlist=None):
        super().__init__(manager)
        self.accent = mode_color("projection")
        self._start(level, seed, locked, playlist)
        self.rotator = SyncRotator()
        self.task = None
        self.task_started = 0.0
        self.answered = False
        self.task_objects = []
        self.option_buttons = []

        self.top_bar = self.own(TopBar("projection", self.go_back))
        self.own(Panel(0.8, 0.62, position=(PANEL_X, 0)))
        self.question = self.own(label("", (PANEL_X - 0.37, 0.255), 1.25, "strong"))
        self.own(label("Представьте, что смотрите на фигуру с этой стороны",
                       (PANEL_X - 0.37, 0.215), 0.8, "muted"))
        self.own(label("Правая кнопка мыши - повернуть фигуру  •  R - исходный вид",
                       (window.top_left.x + 0.05, -0.455), 0.8, "muted"))

        self.feedback = self.own(label("", (PANEL_X, -0.355), 1.0, origin=(0, 0)))
        self.explanation = self.own(label("", (PANEL_X, -0.395), 0.8, "text", origin=(0, 0)))
        self.next_button = self.own(UIButton("Дальше", self.next_task,
                                             position=(window.top_right.x - 0.15, -0.43),
                                             scale=(0.2, 0.06), variant="primary"))
        # После ответа: повернуть фигуру ровно той стороной, о которой спрашивали
        self.look_button = self.own(UIButton("", self.look_from_view,
                                             position=(SHAPE_UI[0], -0.39),
                                             scale=(0.3, 0.055), text_size=0.8))
        self.look_button.enabled = False
        self.setup_hint((window.top_right.x - 0.38, -0.43))
        self.new_task()

    def _start(self, level, seed=None, locked=False, playlist=None):
        """Новая тренировка: свой код и генератор заданий с этим зерном."""
        self.playlist = playlist     # шаг «Моей тренировки» или None
        self.session, seed = new_training("projection", level, seed, locked, playlist)
        self.generator = task_source(self.session, lambda s: ProjectionTaskGenerator(seed=s),
                                     seed)

    def _clear_task_objects(self):
        # Кнопки лежат внутри карточек и удаляются вместе с ними
        for obj in self.task_objects:
            dispose(obj)
        self.task_objects = []
        self.option_buttons = []

    # ---------- 3D-фигура ----------
    def _build_shape(self):
        """Фигура и подписи сторон на общем «шарнире»: при повороте мышью
        подписи поворачиваются вместе с фигурой и стороны не путаются."""
        cells = self.task.shape
        scale = fit_scale(cells, SHAPE_MAX_SIZE)
        holder = Entity(position=ui_to_world(*SHAPE_UI))
        ShapeView(cells, settings.PROJECTION_SHAPE_COLOR, parent=holder, scale=scale)

        # Половины размеров фигуры после масштабирования
        half = [(max(c[i] for c in cells) - min(c[i] for c in cells) + 1) * scale / 2
                for i in range(3)]
        places = {
            "front": (0, -half[1] - 1.1, -half[2] - 0.4),   # перед фигурой, внизу
            "right": (half[0] + 1.9, 0, 0),                 # справа
            "top": (0, half[1] + 1.1, 0),                   # над фигурой
        }
        for view, position in places.items():
            asked = view == self.task.view
            Text(VIEWS[view], parent=holder, position=position, billboard=True,
                 origin=(0, 0), scale=VIEW_LABEL_SCALE * (1.25 if asked else 1),
                 color=color.hex(self.accent if asked else settings.TEXT_MUTED))
        self.task_objects.append(holder)
        self.rotator.set_targets([holder])
        self.rotator.reset()

    # ---------- варианты-картинки ----------
    def _card(self, index, picture, position):
        card = Entity(parent=camera.ui, position=position)
        button = UIButton("", lambda i=index: self.choose(i), parent=card,
                          scale=(CARD_SIZE, CARD_SIZE), radius=0.08)
        label(LETTERS[index], (-CARD_SIZE / 2 + 0.018, CARD_SIZE / 2 - 0.02), 0.8,
              "muted", parent=card)

        cols = max(c for c, _ in picture) + 1
        rows = max(r for _, r in picture) + 1
        cell = min(0.034, 0.14 / max(cols, rows))
        for c, r in picture:
            Entity(parent=card, model="quad", shader=unlit_shader,
                   position=((c - (cols - 1) / 2) * cell, (r - (rows - 1) / 2) * cell - 0.008,
                             FRONT),
                   scale=cell * 0.86, color=color.hex(self.accent))
        self.option_buttons.append(button)
        self.task_objects.append(card)

    def _card_positions(self, count):
        """Карточки рядами по 3, каждый ряд по центру панели."""
        positions = []
        rows = [list(range(count))[i:i + 3] for i in range(0, count, 3)]
        for row_number, row in enumerate(rows):
            y = 0.065 - row_number * CARD_STEP
            for k in range(len(row)):
                positions.append((PANEL_X + (k - (len(row) - 1) / 2) * CARD_STEP, y))
        return positions

    # ---------- задания ----------
    def new_task(self):
        self.task = self.generator.generate(self.session.current_level)
        self.answered = False
        self.task_started = perf_counter()
        self.next_button.text = "Дальше"
        self._clear_task_objects()

        self._build_shape()
        for index, (picture, position) in enumerate(
                zip(self.task.options, self._card_positions(len(self.task.options)))):
            self._card(index, picture, position)

        self.question.text = self.task.question
        self.feedback.text = ""
        self.explanation.text = ""
        self.look_button.enabled = False
        self.reset_hint()
        self._update_status()

    def next_task(self):
        if not self.answered:
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
        self.option_buttons[right].set_variant("correct")
        if correct:
            self.feedback.text = f"Верно!  +{points} баллов"
            self.feedback.color = color.hex(settings.CORRECT_COLOR)
        else:
            self.option_buttons[index].set_variant("wrong")
            self.feedback.text = f"Неверно. Правильный ответ: {LETTERS[right]}"
            self.feedback.color = color.hex(settings.WRONG_COLOR)
            self.explanation.text = textwrap.fill(self.task.explain(index) or "", 72)
        self.look_button.text = f"Посмотреть {VIEWS[self.task.view]}"
        self.look_button.enabled = True
        if self.session.is_finished:
            self.next_button.text = finish_label(self)
        self._update_status()

    def look_from_view(self):
        """Плавно повернуть фигуру так, чтобы была видна спрашиваемая сторона:
        силуэт на экране совпадёт с правильной картинкой."""
        if not self.answered or not self.task_objects:
            return
        pitch, yaw = VIEW_ROTATIONS[self.task.view]
        holder = self.task_objects[0]
        self.rotator.pitch, self.rotator.yaw = pitch, yaw   # мышь продолжит отсюда
        holder.animate_rotation(Vec3(pitch, yaw, 0), duration=TURN_SECONDS,
                                curve=curve.in_out_cubic)

    def _update_status(self):
        self.top_bar.update_state(self.session, self.answered)

    def update(self):
        self.rotator.update()

    def go_back(self):
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
