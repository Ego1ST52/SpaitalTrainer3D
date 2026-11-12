import textwrap

from ursina import *

from core import settings
from interface.ui_kit import FRONT, label, mode_color, Panel, UIButton
from logic.tutorials import TUTORIALS


class TutorialDialog(Entity):
    """Подсказка «Как играть» поверх экрана: три коротких шага и «Понятно»."""

    def __init__(self, mode, on_close, parent=None):
        super().__init__(parent=parent or camera.ui, z=-0.5)
        self.on_close = on_close
        shade = Button(parent=self, model="quad", scale=(4, 2), z=0.05,
                       color=color.rgba(0, 0, 0, 0.6),
                       highlight_color=color.rgba(0, 0, 0, 0.6),
                       pressed_color=color.rgba(0, 0, 0, 0.6))
        shade.on_click = lambda: None          # клики «под» окном не проходят

        accent = mode_color(mode)
        Panel(0.84, 0.42, border=accent, parent=self)
        left = -0.38
        label("Как играть", (left, 0.165), 0.8, accent, parent=self)
        label(settings.MODE_NAMES[mode], (left, 0.125), 1.4, "strong", parent=self)
        for i, line in enumerate(TUTORIALS[mode]):
            y = 0.06 - i * 0.065
            label(str(i + 1), (left + 0.01, y), 1.1, accent, origin=(0, 0), parent=self)
            label(textwrap.fill(line, 62), (left + 0.04, y), 0.8, "text", parent=self)
        UIButton("Понятно", on_close, position=(0.27, -0.165, FRONT * 2), scale=(0.18, 0.055),
                 variant="primary", parent=self)

    def input(self, key):
        if key in ("escape", "enter", "space"):
            self.on_close()
