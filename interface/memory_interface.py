"""Режим «По памяти»: образец показывается несколько секунд и прячется -
фигуру нужно собрать по памяти. Это «Конструирование» с таймером."""

import time as clock

from ursina import *

from interface.construction_interface import ConstructionGameScreen, PANEL_X, PREVIEW_Y
from interface.ui_kit import label

# Сколько секунд виден образец на каждом уровне
SHOW_SECONDS = {"easy": 6, "medium": 5, "hard": 4}


class MemoryGameScreen(ConstructionGameScreen):
    MODE = "memory"

    def __init__(self, *args, **kwargs):
        self.hide_at = 0.0
        self.hidden = False
        self.memory_label = None
        super().__init__(*args, **kwargs)

    def on_task_started(self):
        if self.memory_label is None:
            self.memory_label = self.own(label("", (PANEL_X, PREVIEW_Y - 0.115), 0.8,
                                               "accent", origin=(0, 0)))
        self.hide_at = clock.time() + SHOW_SECONDS[self.session.current_level]
        self.hidden = False
        self.preview.enabled = True

    def can_build(self):
        # Пока образец виден, строить нельзя - иначе это не «по памяти»
        return self.hidden and not self.answered

    def update(self):
        super().update()
        if self.hidden or self.answered:
            return
        left = self.hide_at - clock.time()
        if left > 0:
            self.memory_label.text = f"Запомните фигуру: {left:.0f} с"
        else:
            self.hidden = True
            self.preview.enabled = False
            self.memory_label.text = "Образец спрятан - соберите по памяти"

    def on_checked(self, correct):
        self.preview.enabled = True          # теперь можно сравнить с образцом
        self.memory_label.text = "Сравните с образцом"
