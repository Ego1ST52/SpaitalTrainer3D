from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from interface.ui_kit import FRONT, label, Panel, UIButton
from logic.training_code import parse_code


class CodeDialog(Entity):
    """Окно «Тренировка по коду» поверх меню.
    on_start(mode, level, seed) - код верный, начинаем; on_close() - закрыть."""

    def __init__(self, on_start, on_close):
        super().__init__(parent=camera.ui, z=-0.5)    # поверх меню
        self.on_start = on_start
        self.on_close = on_close

        # Затемнение на весь экран. Это кнопка без действия: она «ловит» клики,
        # чтобы случайно не нажать карточку меню под окном.
        shade = Button(parent=self, model="quad", scale=(4, 2), z=0.05,
                       color=color.rgba(0, 0, 0, 0.6),
                       highlight_color=color.rgba(0, 0, 0, 0.6),
                       pressed_color=color.rgba(0, 0, 0, 0.6))
        shade.on_click = lambda: None

        Panel(0.74, 0.36, parent=self)
        left = -0.33
        label("Тренировка по коду", (left, 0.125), 1.3, "strong", parent=self)
        label("Введите код от друга или учителя, например 31-4821.",
              (left, 0.085), 0.8, "muted", parent=self)
        label("У всех, кто введёт один код, будут одинаковые задания.",
              (left, 0.058), 0.8, "muted", parent=self)

        self.field = InputField(parent=self, position=(-0.08, -0.005, FRONT * 2),
                                scale=(0.5, 0.06), character_limit=8,
                                color=color.hex(settings.BUTTON_COLOR), active=True)
        self.field.limit_content_to = "0123456789- "
        self.field.submit_on = ["enter"]
        self.field.on_submit = self.submit

        self.error = label("", (left, -0.065), 0.85, "wrong", parent=self)
        UIButton("Отмена", self.on_close, position=(0.09, -0.125, FRONT * 2),
                 scale=(0.16, 0.055), variant="ghost", parent=self)
        UIButton("Начать", self.submit, position=(0.26, -0.125, FRONT * 2),
                 scale=(0.16, 0.055), variant="primary", parent=self)

    def submit(self):
        try:
            mode, level, seed = parse_code(self.field.text)
        except ValueError as error:
            self.error.text = str(error)
            return
        self.on_start(mode, level, seed)

    def input(self, key):
        if key == "escape":
            self.on_close()
