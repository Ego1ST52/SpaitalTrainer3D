import textwrap

from ursina import *

from core import settings
from interface.ui_kit import FRONT, label, Panel, UIButton


class ConfirmDialog(Entity):
    """Окно «Вы уверены?» поверх экрана. Для необратимых действий
    (например, удаления игрока): кнопка подтверждения красная."""

    def __init__(self, title, message, confirm_text, on_confirm, on_cancel):
        super().__init__(parent=camera.ui, z=-0.5)     # поверх экрана

        # Затемнение на весь экран «ловит» клики, чтобы не нажать то, что под окном
        shade = Button(parent=self, model="quad", scale=(4, 2), z=0.05,
                       color=color.rgba(0, 0, 0, 0.6),
                       highlight_color=color.rgba(0, 0, 0, 0.6),
                       pressed_color=color.rgba(0, 0, 0, 0.6))
        shade.on_click = lambda: None

        Panel(0.74, 0.32, border=settings.WRONG_COLOR, parent=self)
        left = -0.33
        label(title, (left, 0.105), 1.25, "strong", parent=self)
        label(textwrap.fill(message, 60), (left, 0.035), 0.8, "text", parent=self)
        UIButton("Отмена", on_cancel, position=(0.09, -0.11, FRONT * 2), scale=(0.16, 0.055),
                 variant="ghost", parent=self)
        UIButton(confirm_text, on_confirm, position=(0.26, -0.11, FRONT * 2),
                 scale=(0.16, 0.055), variant="wrong", parent=self)
        self.on_cancel = on_cancel

    def input(self, key):
        if key == "escape":
            self.on_cancel()
