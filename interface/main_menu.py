from ursina import *

from core import settings
from interface.base_screen import BaseScreen

LEVELS = [("easy", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")]


class MainMenu(BaseScreen):
    def __init__(self, manager):
        super().__init__(manager)
        self.level = "easy"
        self.level_buttons = {}

        self.own(Text("Spatial Trainer 3D", origin=(0, 0), position=(0, 0.38),
                      scale=2.6, color=color.hex(settings.ACCENT)))
        self.own(Text("Тренажёр пространственного мышления", origin=(0, 0),
                      position=(0, 0.29), scale=1.2,
                      color=color.hex(settings.TEXT_COLOR)))

        self._button("Вращение куба", 0.14, lambda: self.start("rotation"))
        self._button("Одинаковые фигуры", 0.04, lambda: self.start("matching"))

        self.own(Text("Сложность", origin=(0, 0), position=(0, -0.08),
                      scale=1.2, color=color.hex(settings.TEXT_COLOR)))
        for i, (key, name) in enumerate(LEVELS):
            button = self._button(name, -0.16,
                                  lambda k=key: self.set_level(k),
                                  scale=(0.25, 0.07), x=(i - 1) * 0.27)
            self.level_buttons[key] = button

        self._button("Статистика", -0.27, lambda: self.navigate("statistics"),
                     scale=(0.4, 0.07))
        self._button("Выход", -0.37, application.quit, scale=(0.25, 0.07))
        self.set_level("easy")

    def _button(self, label, y, action, scale=(0.4, 0.08), x=0):
        button = Button(text=label, color=color.hex(settings.BUTTON_COLOR),
                        highlight_color=color.hex(settings.BUTTON_HOVER),
                        scale=scale, position=(x, y))
        button.on_click = action
        return self.own(button)

    def set_level(self, level):
        self.level = level
        for key, button in self.level_buttons.items():
            chosen = settings.SELECTED_COLOR if key == level else settings.BUTTON_COLOR
            button.color = color.hex(chosen)

    def start(self, mode):
        self.navigate(mode, level=self.level)