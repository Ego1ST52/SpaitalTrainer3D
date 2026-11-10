from datetime import datetime

from ursina import *

from core import settings
from data.statistics import summarize
from interface.base_screen import BaseScreen
from logic.session import format_duration

COLUMNS = [("Дата", -0.62), ("Режим", -0.42), ("Уровень", -0.12),
           ("Верно", 0.1), ("Баллы", 0.25), ("Время", 0.4)]
MAX_ROWS = 10


class StatisticsScreen(BaseScreen):
    """История тренировок. history: список словарей или None, если база недоступна."""

    def __init__(self, manager, history):
        super().__init__(manager)
        accent = color.hex(settings.ACCENT)
        text_color = color.hex(settings.TEXT_COLOR)

        self.own(Text("Статистика", origin=(0, 0), position=(0, 0.4),
                      scale=2.2, color=accent))

        if history is None:
            self._message("Не удалось прочитать данные из базы.", color.hex(settings.WRONG_COLOR))
        elif not history:
            self._message("Пока нет сохранённых тренировок. "
                          "Пройдите тренировку, и результат появится здесь.", text_color)
        else:
            self._show(history, accent, text_color)

        self._button("В меню", (-0.17, -0.4), lambda: self.navigate("menu"))
        self._button("Прогресс", (0.17, -0.4), lambda: self.navigate("progress"))

        self.own(Text("Показатели отражают результаты в игре и не доказывают "
                      "изменения когнитивных способностей.",
                      origin=(0, 0), position=(0, -0.46), scale=0.9,
                      color=color.hex("#64748b")))

    def _button(self, label, position, action):
        button = Button(text=label, color=color.hex(settings.BUTTON_COLOR),
                        highlight_color=color.hex(settings.BUTTON_HOVER),
                        scale=(0.3, 0.07), position=position)
        button.on_click = action
        self.own(button)

    def _message(self, text, text_color):
        self.own(Text(text, origin=(0, 0), position=(0, 0.1), scale=1.2,
                      color=text_color))

    def _show(self, history, accent, text_color):
        s = summarize(history)
        self.own(Text(f"Тренировок: {s['sessions']}   Заданий: {s['tasks']}   "
                      f"Точность: {s['accuracy']:.0f}%",
                      origin=(0, 0), position=(0, 0.31), scale=1.3, color=text_color))
        self.own(Text(f"Всего баллов: {s['points']}   Лучший результат: {s['best_points']}   "
                      f"Среднее время на задание: {s['average_seconds']:.1f} с",
                      origin=(0, 0), position=(0, 0.25), scale=1.3, color=text_color))

        for title, x in COLUMNS:
            self.own(Text(title, position=(x, 0.17), scale=1.0, color=accent))

        for row, h in enumerate(history[:MAX_ROWS]):
            y = 0.12 - row * 0.045
            played = datetime.fromisoformat(h["played_at"]).strftime("%d.%m %H:%M")
            values = [
                played,
                settings.MODE_NAMES.get(h["mode"], h["mode"]),
                settings.LEVEL_NAMES.get(h["level"], h["level"]),
                f"{h['tasks_correct']}/{h['tasks_total']}",
                str(h["points"]),
                format_duration(h["total_seconds"]),
            ]
            for (_, x), value in zip(COLUMNS, values):
                self.own(Text(value, position=(x, y), scale=1.0, color=text_color))