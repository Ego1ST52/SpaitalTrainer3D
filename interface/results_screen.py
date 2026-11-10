from ursina import *

from core import settings
from interface.base_screen import BaseScreen
from logic.session import format_duration


class ResultsScreen(BaseScreen):
    """Итоги тренировки. saved=False, если результат не удалось сохранить."""

    def __init__(self, manager, session, saved=True):
        super().__init__(manager)
        s = session
        accent = color.hex(settings.ACCENT)
        text_color = color.hex(settings.TEXT_COLOR)

        self.own(Text("Тренировка завершена", origin=(0, 0), position=(0, 0.4),
                      scale=2.2, color=accent))
        self.own(Text(f"{settings.MODE_NAMES[s.mode]}. "
                      f"Уровень: {settings.LEVEL_NAMES[s.level]}",
                      origin=(0, 0), position=(0, 0.32), scale=1.2,
                      color=text_color))

        lines = [
            f"Верно: {s.correct} из {s.total}",
            f"Ошибок: {s.wrong}",
            f"Точность: {s.accuracy:.0f}%",
            f"Время: {format_duration(s.total_time)}",
            f"Среднее время на задание: {s.average_time:.1f} с",
            f"Баллы: {s.points}",
        ]
        self.own(Text("\n".join(lines), origin=(0, 0), position=(0, 0.08),
                      scale=1.6, color=text_color))

        self._button("Тренироваться ещё", -0.14,
                     lambda: self.navigate(s.mode, level=s.level))
        self._button("В меню", -0.24, lambda: self.navigate("menu"))

        if not saved:
            self.own(Text("Не удалось сохранить результат в базу данных.",
                          origin=(0, 0), position=(0, -0.34), scale=1.1,
                          color=color.hex(settings.WRONG_COLOR)))

        self.own(Text("Баллы отражают результат в этой игре и не являются "
                      "измерением когнитивных способностей.",
                      origin=(0, 0), position=(0, -0.42), scale=0.9,
                      color=color.hex("#64748b")))

    def _button(self, label, y, action):
        button = Button(text=label, color=color.hex(settings.BUTTON_COLOR),
                        highlight_color=color.hex(settings.BUTTON_HOVER),
                        scale=(0.4, 0.08), position=(0, y))
        button.on_click = action
        self.own(button)