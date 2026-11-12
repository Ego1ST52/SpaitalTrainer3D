"""Общий экран для режимов «задание с вариантами ответа».

Здесь всё, что у таких режимов одинаково: верхняя панель, панель с вопросом,
карточки вариантов, проверка ответа, баллы, «Дальше», смена уровня клавишами
1-2-3 и переход к итогам. Конкретный режим наследует этот класс и дописывает
только своё: генератор заданий, 3D-сцену и то, как нарисовать вариант.
"""

from time import perf_counter

from ursina import *

from core import settings
from engine.objects import dispose
from interface.base_screen import BaseScreen
from interface.game_common import (LEVEL_KEYS, finish_label, finish_training, new_training,
                                     task_source)
from interface.hint_control import HintMixin
from interface.ui_kit import label, mode_color, Panel, TopBar, UIButton
from logic.answer_checker import check_answer

LETTERS = "АБВГДЕ"


def draw_picture(card, picture, hex_color, size=0.14):
    """Плоская картинка из клеток (столбец, строка) внутри карточки варианта."""
    from ursina.shaders import unlit_shader
    from interface.ui_kit import FRONT
    cols = max(c for c, _ in picture) + 1
    rows = max(r for _, r in picture) + 1
    cell = min(0.034, size / max(cols, rows))
    for c, r in picture:
        Entity(parent=card, model="quad", shader=unlit_shader,
               position=((c - (cols - 1) / 2) * cell, (r - (rows - 1) / 2) * cell - 0.008, FRONT),
               scale=cell * 0.86, color=color.hex(hex_color))


class ChoiceGameScreen(HintMixin, BaseScreen):
    MODE = None              # ключ режима, например "nets"
    HINT = ""                # подсказка внизу экрана
    PANEL_X = 0.42           # центр правой панели
    CARD_W = 0.2
    CARD_H = 0.2
    COLUMNS = 3
    OPTION_TEXT_SIZE = 1.6   # размер текста на карточке-варианте

    def __init__(self, manager, level="easy", seed=None, locked=False, playlist=None):
        super().__init__(manager)
        self.accent = mode_color(self.MODE)
        self._start(level, seed, locked, playlist)
        self.task = None
        self.task_started = 0.0
        self.answered = False
        self.task_objects = []        # всё, что пересоздаётся для каждого задания
        self.option_buttons = []

        self.top_bar = self.own(TopBar(self.MODE, self.go_back))
        self.own(Panel(0.8, 0.62, position=(self.PANEL_X, 0)))
        self.question = self.own(label("", (self.PANEL_X - 0.37, 0.255), 1.2, "strong"))
        self.subtitle = self.own(label("", (self.PANEL_X - 0.37, 0.215), 0.8, "muted"))
        if self.HINT:
            self.own(label(self.HINT, (window.top_left.x + 0.05, -0.455), 0.8, "muted"))
        self.feedback = self.own(label("", (self.PANEL_X, -0.37), 1.0, origin=(0, 0)))
        self.next_button = self.own(UIButton("Дальше", self.next_task,
                                             position=(window.top_right.x - 0.15, -0.43),
                                             scale=(0.2, 0.06), variant="primary"))
        self.setup_hint((window.top_right.x - 0.38, -0.43))
        self.new_task()

    # ---------- что дописывает конкретный режим ----------
    def make_generator(self, seed):
        raise NotImplementedError

    def build_scene(self):
        """3D-часть задания. Созданное добавлять в self.task_objects."""

    def subtitle_text(self):
        return ""

    def option_text(self, index, option):
        """Текст на карточке варианта (или None - тогда рисует draw_option)."""
        return None

    def draw_option(self, index, option, card):
        """Нарисовать вариант внутри карточки card (если нет текста)."""

    def answer_text(self):
        return f"Правильный ответ: {LETTERS[self.task.correct_index]}"

    def after_answer(self, correct):
        """Что показать после ответа (например, анимацию решения)."""

    # ---------- общее ----------
    def _start(self, level, seed=None, locked=False, playlist=None):
        self.playlist = playlist
        self.session, seed = new_training(self.MODE, level, seed, locked, playlist)
        self.generator = task_source(self.session, self.make_generator, seed)

    def _clear_task_objects(self):
        for obj in self.task_objects:
            dispose(obj)
        self.task_objects = []
        self.option_buttons = []

    def card_positions(self, count):
        """Карточки рядами по COLUMNS, каждый ряд по центру панели."""
        positions = []
        step_x, step_y = self.CARD_W + 0.04, self.CARD_H + 0.04
        rows = [list(range(count))[i:i + self.COLUMNS] for i in range(0, count, self.COLUMNS)]
        top = 0.07 if len(rows) > 1 else -0.03
        for row_number, row in enumerate(rows):
            for k in range(len(row)):
                positions.append((self.PANEL_X + (k - (len(row) - 1) / 2) * step_x,
                                  top - row_number * step_y))
        return positions

    def _card(self, index, option, position):
        card = Entity(parent=camera.ui, position=position)
        text = self.option_text(index, option)
        button = UIButton(text or "", lambda i=index: self.choose(i), parent=card,
                          scale=(self.CARD_W, self.CARD_H), radius=0.08,
                          text_size=self.OPTION_TEXT_SIZE if text else 0.9)
        if text is None:
            label(LETTERS[index], (-self.CARD_W / 2 + 0.018, self.CARD_H / 2 - 0.02), 0.8,
                  "muted", parent=card)
            self.draw_option(index, option, card)
        self.option_buttons.append(button)
        self.task_objects.append(card)

    def new_task(self):
        self.task = self.generator.generate(self.session.current_level)
        self.answered = False
        self.task_started = perf_counter()
        self.next_button.text = "Дальше"
        self._clear_task_objects()
        self.build_scene()
        for index, (option, position) in enumerate(
                zip(self.task.options, self.card_positions(len(self.task.options)))):
            self._card(index, option, position)
        self.question.text = self.task.question
        self.subtitle.text = self.subtitle_text()
        self.feedback.text = ""
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
        self.top_bar.flash_level(self.session)

        right = self.task.correct_index
        self.option_buttons[right].set_variant("correct")
        if correct:
            self.feedback.text = f"Верно!  +{points} баллов"
            self.feedback.color = color.hex(settings.CORRECT_COLOR)
        else:
            self.option_buttons[index].set_variant("wrong")
            self.feedback.text = f"Неверно. {self.answer_text()}"
            self.feedback.color = color.hex(settings.WRONG_COLOR)
        if self.session.is_finished:
            self.next_button.text = finish_label(self)
        self._update_status()
        self.after_answer(correct)

    def on_option_removed(self, index):
        """Вычеркнутый подсказкой вариант: картинка на карточке почти гаснет."""
        button = self.option_buttons[index]
        for child in button.parent.children:
            if child is not button:
                child.alpha = 0.18
                for part in child.children:
                    part.alpha = 0.18

    def _update_status(self):
        self.top_bar.update_state(self.session, self.answered)

    def go_back(self):
        self.navigate("menu")

    def close(self):
        self._clear_task_objects()
        super().close()

    def input(self, key):
        if key in LEVEL_KEYS and not self.session.locked:
            self._start(LEVEL_KEYS[key])  # заново, с новым кодом
            self.new_task()
        elif key == "h":
            self.use_hint()
