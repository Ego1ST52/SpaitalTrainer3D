from datetime import datetime

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from data.statistics import summarize, accuracy_of
from interface.base_screen import BaseScreen
from interface.ui_kit import FRONT, label, Panel, StatTile, UIButton
from logic.session import format_duration

# Таблица: (заголовок, x левого края колонки)
COLUMNS = [("Дата", -0.74), ("Режим", -0.5), ("Уровень", -0.18), ("Верно", 0.06),
           ("Точность", 0.22), ("Баллы", 0.4), ("Время", 0.56)]
MAX_ROWS = 8
TABLE_TOP = 0.08
ROW_STEP = 0.045


class StatisticsScreen(BaseScreen):
    """История тренировок. history: список словарей или None, если база недоступна."""

    def __init__(self, manager, history):
        super().__init__(manager)
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05

        self.own(label("Статистика", (left, 0.42), 2.0, "strong"))
        self.own(label("Ваши тренировки и общие показатели", (left, 0.365), 0.85, "muted"))
        self.own(UIButton("Прогресс", lambda: self.navigate("progress"),
                          position=(right - 0.32, 0.42), scale=(0.2, 0.06),
                          variant="primary"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06),
                          variant="ghost"))

        self.own(Panel(1.62, 0.5, position=(0, -0.105)))

        if history is None:
            self._message("Не удалось прочитать данные из базы.", "wrong")
        elif not history:
            self._message("Здесь появятся ваши тренировки. "
                          "Пройдите первую - и результат сохранится.", "text")
        else:
            self._summary(history)
            self._table(history)

        self.own(label("Показатели отражают результаты в игре и не доказывают "
                       "изменения когнитивных способностей.",
                       (0, -0.45), 0.8, "muted", origin=(0, 0)))

    def _message(self, text, tone):
        self.own(label(text, (0, -0.1), 1.0, tone, origin=(0, 0)))

    def _summary(self, history):
        s = summarize(history)
        tiles = [
            ("Тренировок", str(s["sessions"]), "strong"),
            ("Заданий", str(s["tasks"]), "strong"),
            ("Точность", f"{s['accuracy']:.0f}%", "accent"),
            ("Всего баллов", str(s["points"]), "strong"),
            ("Лучший результат", str(s["best_points"]), "strong"),
            ("Среднее на задание", f"{s['average_seconds']:.1f} с", "strong"),
        ]
        width, gap = 0.255, 0.018
        start = -(len(tiles) * width + (len(tiles) - 1) * gap) / 2 + width / 2
        for i, (caption, value, tone) in enumerate(tiles):
            self.own(StatTile(caption, value, (start + i * (width + gap), 0.23),
                              width=width, tone=tone))

    def _table(self, history):
        for title, x in COLUMNS:
            self.own(label(title, (x, TABLE_TOP), 0.8, "muted"))

        for row, h in enumerate(history[:MAX_ROWS]):
            y = TABLE_TOP - 0.05 - row * ROW_STEP
            # тонкая линия-разделитель над строкой
            self.own(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                            position=(0, y + ROW_STEP / 2, FRONT / 2),
                            scale=(1.56, 0.0015), color=color.hex(settings.BORDER)))
            played = datetime.fromisoformat(h["played_at"]).strftime("%d.%m  %H:%M")
            values = [
                (played, "muted"),
                (settings.MODE_NAMES.get(h["mode"], h["mode"]), "text"),
                (settings.LEVEL_NAMES.get(h["level"], h["level"]), "text"),
                (f"{h['tasks_correct']}/{h['tasks_total']}", "text"),
                (f"{accuracy_of(h):.0f}%", "accent"),
                (str(h["points"]), "strong"),
                (format_duration(h["total_seconds"]), "text"),
            ]
            for (_, x), (value, tone) in zip(COLUMNS, values):
                self.own(label(value, (x, y), 0.9, tone))

        hidden = len(history) - MAX_ROWS
        if hidden > 0:
            self.own(label(f"и ещё {hidden} более ранних", (COLUMNS[0][1], -0.33),
                           0.75, "muted"))
