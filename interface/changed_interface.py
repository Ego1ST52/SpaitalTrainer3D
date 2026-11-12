"""Режим «Что изменилось?»: запомнить фигуру, потом найти переставленный кубик."""

import textwrap
import time as clock
from time import perf_counter

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.objects import ShadedBlock, dispose
from interface.base_screen import BaseScreen
from interface.game_common import (LEVEL_KEYS, finish_label, finish_training, new_training,
                                   task_source)
from interface.ui_kit import label, mode_color, Panel, TopBar, UIButton
from logic.changed import ChangedTaskGenerator, is_answer

PANEL_X = 0.62
PANEL_WIDTH = 0.44
PANEL_LEFT = PANEL_X - PANEL_WIDTH / 2 + 0.03
HOVER_COLOR = "#f8fafc"


class ChangedGameScreen(BaseScreen):
    MODE = "changed"

    def __init__(self, manager, level="easy", seed=None, locked=False, playlist=None):
        super().__init__(manager)
        self.accent = mode_color(self.MODE)
        self._start(level, seed, locked, playlist)
        self.task = None
        self.blocks = {}              # клетка -> кубик на экране
        self.extra = []               # «призрак» старого места и т.п.
        self.answered = False
        self.hidden_at = 0.0          # когда фигуру меняют
        self.changed = False          # фигура уже изменена (можно отвечать)
        self.task_started = 0.0
        self.hovered = None

        # Фигура стоит слева; её чуть наклоняем, чтобы были видны три стороны
        self.holder = self.own(Entity(rotation=(20, 35, 0)))
        self.top_bar = self.own(TopBar(self.MODE, self.go_back))
        self.own(Panel(PANEL_WIDTH, 0.78, position=(PANEL_X, -0.06)))
        self.question = self.own(label("", (PANEL_LEFT, 0.27), 0.95, "strong",
                                       origin=(-0.5, 0.5)))
        self.phase = self.own(label("", (PANEL_LEFT, 0.12), 0.9, "accent"))
        self.feedback = self.own(label("", (PANEL_LEFT, -0.12), 0.85, origin=(-0.5, 0.5)))
        self.next_button = self.own(UIButton("Дальше", self.next_task,
                                             position=(PANEL_X, -0.415),
                                             scale=(PANEL_WIDTH - 0.06, 0.06),
                                             variant="primary"))
        self.own(label("Правая кнопка мыши - осмотреть фигуру  •  клик по кубику - ответ",
                       (window.top_left.x + 0.05, -0.455), 0.8, "muted"))
        self.new_task()

    def _start(self, level, seed=None, locked=False, playlist=None):
        self.playlist = playlist
        self.session, seed = new_training(self.MODE, level, seed, locked, playlist)
        self.generator = task_source(self.session, lambda s: ChangedTaskGenerator(seed=s),
                                     seed)

    # ---------- фигура ----------
    def _show(self, cells):
        for block in self.blocks.values():
            dispose(block)
        self.blocks = {}
        center = [(max(c[i] for c in self.task.before) + min(c[i] for c in self.task.before))
                  / 2 for i in range(3)]
        for cell in cells:
            block = ShadedBlock(self.accent, parent=self.holder,
                                position=tuple(cell[i] - center[i] for i in range(3)))
            block.cell = cell
            self.blocks[cell] = block
        self.center = center

    def _clear_extra(self):
        for obj in self.extra:
            dispose(obj)
        self.extra = []

    def new_task(self):
        self.task = self.generator.generate(self.session.current_level)
        self.answered = False
        self.changed = False
        self.hovered = None
        self._clear_extra()
        self._show(self.task.before)
        self.hidden_at = clock.time() + self.task.show_seconds
        self.question.text = textwrap.fill("Запомните фигуру. Потом один кубик "
                                           "переставят - найдите его.", 30)
        self.feedback.text = ""
        self.next_button.text = "Дальше"
        self.top_bar.update_state(self.session, False)

    def change_now(self):
        """Переставить кубик (время запоминания вышло)."""
        if self.changed:
            return
        self.changed = True
        self._show(self.task.after)
        self.task_started = perf_counter()
        self.question.text = textwrap.fill(self.task.question, 30)
        self.phase.text = "Кубик переставлен"

    def update(self):
        if not self.changed and not self.answered:
            left = self.hidden_at - clock.time()
            if left > 0:
                self.phase.text = f"Запомните: {left:.0f} с"
            else:
                self.change_now()
            return
        if self.answered:
            return
        hit = mouse.hovered_entity
        block = hit if hit is not None and getattr(hit, "cell", None) in self.blocks else None
        if block is not self.hovered:
            for item in self.blocks.values():
                item.set_color(HOVER_COLOR if item is block else self.accent)
            self.hovered = block

    def input(self, key):
        if key in LEVEL_KEYS and not self.session.locked:
            self._start(LEVEL_KEYS[key])
            self.new_task()
        elif key == "left mouse down" and self.changed and not self.answered:
            hit = mouse.hovered_entity
            if hit is not None and getattr(hit, "cell", None) in self.blocks:
                self.choose(hit.cell)

    # ---------- ответ ----------
    def choose(self, cell):
        if self.answered or not self.changed:
            return
        self.answered = True
        seconds = perf_counter() - self.task_started
        correct = is_answer(self.task, cell)
        points = self.session.record(correct, seconds, self.task.tags)
        self.top_bar.flash_level(self.session)
        for item in self.blocks.values():
            item.set_color(self.accent)
        self.blocks[self.task.added].set_color(settings.CORRECT_COLOR)
        if correct:
            self.feedback.text = f"Верно!  +{points} баллов"
            self.feedback.color = color.hex(settings.CORRECT_COLOR)
        else:
            self.blocks[tuple(cell)].set_color(settings.WRONG_COLOR)
            self.feedback.text = textwrap.fill("Неверно. Переставлен зелёный кубик.", 34)
            self.feedback.color = color.hex(settings.WRONG_COLOR)
        # Прозрачный кубик - где он стоял раньше
        good = color.hex(settings.CORRECT_COLOR)
        self.extra.append(Entity(parent=self.holder, model="cube", scale=0.9,
                                 position=tuple(self.task.removed[i] - self.center[i]
                                                for i in range(3)),
                                 color=color.rgba(good.r, good.g, good.b, 0.35),
                                 shader=unlit_shader))
        self.feedback.text += "\n" + textwrap.fill("Прозрачный - где он стоял раньше.", 34)
        self.phase.text = ""
        if self.session.is_finished:
            self.next_button.text = finish_label(self)
        self.top_bar.update_state(self.session, True)

    def next_task(self):
        if not self.answered:
            return
        if self.session.is_finished:
            finish_training(self)
        else:
            self.new_task()

    def go_back(self):
        self.navigate("menu")

    def close(self):
        self._clear_extra()
        for block in self.blocks.values():
            dispose(block)
        self.blocks = {}
        super().close()
