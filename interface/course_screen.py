"""Экран «Путь новичка»: уроки по порядку, пройденные отмечены,
следующие закрыты, пока не пройден текущий."""

import textwrap

from ursina import *

from engine.backdrop import FloatingCubes
from interface.base_screen import BaseScreen
from interface.ui_kit import label, mode_color, Panel, UIButton
from logic.course import LESSONS, lesson_playlist, state

CARD_W = 0.31
CARD_H = 0.3
COLUMNS = 5


class CourseScreen(BaseScreen):
    """progress - сколько уроков пройдено, message - что сказать сверху."""

    def __init__(self, manager, progress, message=""):
        super().__init__(manager)
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(FloatingCubes())
        self.own(label("Путь новичка", (left, 0.42), 2.0, "strong"))
        done = min(progress, len(LESSONS))
        self.own(label(message or f"Пройдено уроков: {done} из {len(LESSONS)}. "
                       "Каждый следующий открывается после предыдущего.",
                       (left, 0.365), 0.85, "accent" if message else "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06), variant="ghost"))
        for index, lesson in enumerate(LESSONS):
            row, col = divmod(index, COLUMNS)
            x = (col - (COLUMNS - 1) / 2) * (CARD_W + 0.03)
            y = 0.13 - row * (CARD_H + 0.06)
            self._card(index, lesson, state(index, progress), x, y)

    def _card(self, index, lesson, status, x, y):
        accent = mode_color(lesson.steps[0][0])
        dim = status == "locked"
        self.own(Panel(CARD_W, CARD_H, position=(x, y),
                       border=accent if status == "open" else None))
        top = y + CARD_H / 2
        mark = {"done": "пройден", "open": "следующий", "locked": "закрыт"}[status]
        tone = {"done": "correct", "open": accent, "locked": "muted"}[status]
        self.own(label(f"{index + 1:02d}", (x - CARD_W / 2 + 0.02, top - 0.03), 1.0,
                       "muted" if dim else accent))
        self.own(label(mark, (x + CARD_W / 2 - 0.02, top - 0.03), 0.7, tone,
                       origin=(0.5, 0)))
        self.own(label(lesson.title, (x - CARD_W / 2 + 0.02, top - 0.075), 1.0,
                       "muted" if dim else "strong"))
        self.own(label(textwrap.fill(lesson.tip, 26), (x - CARD_W / 2 + 0.02, top - 0.1),
                       0.68, "muted" if dim else "text", origin=(-0.5, 0.5)))
        self.own(label(f"цель: {lesson.goal}% верных", (x - CARD_W / 2 + 0.02, y - 0.07),
                       0.65, "muted"))
        if not dim:
            self.own(UIButton("Повторить" if status == "done" else "Начать урок",
                              lambda i=index: self.start(i), position=(x, y - CARD_H / 2 + 0.04),
                              scale=(CARD_W - 0.04, 0.05), text_size=0.75,
                              variant="primary" if status == "open" else "secondary"))
        else:
            self.own(label("откроется после урока " + str(index), (x, y - CARD_H / 2 + 0.04),
                           0.68, "muted", origin=(0, 0)))

    def start(self, index):
        playlist = lesson_playlist(index)
        self.navigate(playlist.current[0], playlist=playlist)
