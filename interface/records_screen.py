"""Экран «Рекорды»: таблица игроков на этом компьютере."""

from ursina import *

from engine.objects import dispose
from interface.base_screen import BaseScreen
from interface.progress_screen import MODES_ROW_1, MODES_ROW_2
from interface.ui_kit import label, Panel, Segmented, UIButton
from logic.leaderboard import leaderboard

GOLD = "#fbbf24"
MAX_ROWS = 8
# Столбцы: (заголовок, x, выравнивание)
COLUMNS = [("Место", -0.7, (-0.5, 0)), ("Игрок", -0.58, (-0.5, 0)),
           ("Рекорд", 0.02, (0.5, 0)), ("Точность", 0.22, (0.5, 0)),
           ("Тренировок", 0.45, (0.5, 0)), ("Баллов всего", 0.7, (0.5, 0))]


class RecordsScreen(BaseScreen):
    """players - [(имя, история)] или None, если база недоступна."""

    def __init__(self, manager, players, current_name=None):
        super().__init__(manager)
        self.players = players
        self.current_name = current_name
        self.rows = []                       # строки таблицы (пересоздаются)
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(label("Рекорды", (left, 0.42), 2.0, "strong"))
        self.own(label("Рекорд - больше всего баллов за одну тренировку", (left, 0.365),
                       0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06), variant="ghost"))
        if players is None:
            self.own(label("Не удалось прочитать данные из базы.", (0, 0.1), 1.0, "wrong",
                           origin=(0, 0)))
            return
        self.switch_1 = self.own(Segmented(MODES_ROW_1, None, self.set_mode,
                                           position=(-0.42, 0.27), width=0.78,
                                           text_size=0.75, height=0.05))
        self.switch_2 = self.own(Segmented(MODES_ROW_2, None, self.set_mode,
                                           position=(0.42, 0.27), width=0.78,
                                           text_size=0.75, height=0.05))
        self.switch_2.clear()
        self.own(Panel(1.62, 0.6, position=(0, -0.08)))
        for title, x, origin in COLUMNS:
            self.own(label(title, (x, 0.17), 0.8, "muted", origin=origin))
        self.set_mode(None)

    def set_mode(self, mode):
        if mode in dict(MODES_ROW_1):
            self.switch_2.clear()
        else:
            self.switch_1.clear()
        for row in self.rows:
            dispose(row)
        self.rows = []
        table = leaderboard(self.players, mode)
        if not table:
            self.rows.append(label("В этом режиме ещё никто не тренировался.", (0, 0), 1.0,
                                   "muted", origin=(0, 0)))
            return
        for i, row in enumerate(table[:MAX_ROWS]):
            y = 0.11 - i * 0.06
            tone = GOLD if row.place == 1 else ("accent" if row.name == self.current_name
                                                else "text")
            values = [str(row.place), row.name, str(row.best), f"{row.accuracy:.0f}%",
                      str(row.trainings), str(row.total)]
            for value, (_, x, origin) in zip(values, COLUMNS):
                self.rows.append(label(value, (x, y), 1.0, tone, origin=origin))

    def close(self):
        for row in self.rows:
            dispose(row)
        self.rows = []
        super().close()
