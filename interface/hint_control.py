"""Кнопка «Подсказка» для режимов с вариантами ответа (общая для всех экранов).

Экран, который её использует, должен иметь self.task (с correct_index и
options), self.option_buttons, self.answered и вызывать:
  setup_hint(...)  - один раз при создании экрана;
  reset_hint()     - при каждом новом задании;
  hint_blocked(i)  - в choose(): по вычеркнутому варианту клик не считается;
  hints_used       - сколько подсказок взято (передать в session.record);
  close_hint()     - после ответа.
"""

import random

from interface.ui_kit import UIButton
from logic.hints import hints_left, pick_hint


class HintMixin:
    def setup_hint(self, position, scale=(0.21, 0.06), text_size=0.8):
        self._hint_rng = random.Random()
        self.removed_options = set()
        self.hint_button = self.own(UIButton("Подсказка  -50%", self.use_hint,
                                             position=position, scale=scale,
                                             text_size=text_size, variant="ghost"))

    @property
    def hints_used(self):
        return len(self.removed_options)

    def reset_hint(self):
        self.removed_options = set()
        allowed = not getattr(self.session, "no_hints", False)     # в тесте подсказок нет
        self.hint_button.enabled = allowed and hints_left(len(self.task.options), set()) > 0

    def hint_blocked(self, index):
        return index in self.removed_options

    def use_hint(self):
        """Вычеркнуть один неверный вариант. Баллы за задание - вдвое меньше."""
        if self.answered or not self.hint_button.enabled:
            return None
        index = pick_hint(self.task.correct_index, len(self.task.options),
                          self.removed_options, self._hint_rng)
        if index is None:
            return None
        self.removed_options.add(index)
        self.option_buttons[index].strike()
        self.on_option_removed(index)
        self.hint_button.enabled = hints_left(len(self.task.options),
                                              self.removed_options) > 0
        return index

    def on_option_removed(self, index):
        """Что ещё погасить, кроме кнопки (например, 3D-фигуру варианта)."""

    def close_hint(self):
        self.hint_button.enabled = False
