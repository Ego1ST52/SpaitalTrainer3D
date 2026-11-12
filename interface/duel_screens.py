"""Экраны «Игры вдвоём»: выбор участников, передача хода, итоги дуэли."""

from ursina import *

from core import settings
from engine.backdrop import FloatingCubes
from interface.base_screen import BaseScreen
from interface.ui_kit import Avatar, label, mode_color, Panel, Segmented, UIButton
from logic.duel import Duel
from logic.session import format_duration

LEVELS = [("easy", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")]
MODES_ROW_1 = [("rotation", "Вращение"), ("matching", "Фигуры"), ("projection", "Проекции"),
               ("construction", "Сборка"), ("nets", "Развёртка")]
MODES_ROW_2 = [("sections", "Сечения"), ("count", "Кубики"), ("memory", "Память"),
               ("shadow", "Тень"), ("reverse", "Повороты"), ("symmetry", "Симметрия"),
               ("views", "По видам")]
GOLD = "#fbbf24"


class DuelSetupScreen(BaseScreen):
    """Кто играет, в каком режиме и на каком уровне. users - список игроков."""

    def __init__(self, manager, users, current_id):
        super().__init__(manager)
        self.users = users or []
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(FloatingCubes())
        self.own(label("Игра вдвоём", (left, 0.42), 2.0, "strong"))
        self.own(label("Оба игрока по очереди проходят одни и те же задания", (left, 0.365),
                       0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06), variant="ghost"))

        if len(self.users) < 2:
            self.own(label("Для игры вдвоём нужны хотя бы два игрока.", (0, 0.1), 1.1,
                           "text", origin=(0, 0)))
            self.own(UIButton("Добавить игрока", lambda: self.navigate("profiles"),
                              position=(0, -0.0), scale=(0.3, 0.065), variant="primary"))
            return

        ids = [u["id"] for u in self.users]
        first = current_id if current_id in ids else ids[0]
        second = next(i for i in ids if i != first)
        options = [(u["id"], u["name"]) for u in self.users[:5]]
        self.own(label("Первый игрок", (left, 0.27), 0.9))
        self.first = self.own(Segmented(options, first, self._changed,
                                        position=(0.05, 0.27), width=1.4))
        self.own(label("Второй игрок", (left, 0.18), 0.9))
        self.second = self.own(Segmented(options, second, self._changed,
                                         position=(0.05, 0.18), width=1.4))

        self.own(label("Режим", (left, 0.07), 0.9))
        self.mode = "rotation"
        self.modes_1 = self.own(Segmented(MODES_ROW_1, "rotation", self._mode,
                                          position=(0.05, 0.07), width=1.4, text_size=0.8))
        self.modes_2 = self.own(Segmented(MODES_ROW_2, None, self._mode,
                                          position=(0.05, 0.005), width=1.4, text_size=0.8))
        self.modes_2.clear()
        self.own(label("Уровень", (left, -0.09), 0.9))
        self.level = self.own(Segmented(LEVELS, "easy", lambda _: None,
                                        position=(0.05, -0.09), width=1.4))
        self.error = self.own(label("", (0, -0.19), 0.9, "wrong", origin=(0, 0)))
        self.own(UIButton("Начать дуэль", self.start, position=(0, -0.28), scale=(0.34, 0.07),
                          variant="primary"))

    def _changed(self, _):
        self.error.text = ""

    def _mode(self, mode):
        self.mode = mode
        (self.modes_2 if mode in dict(MODES_ROW_1) else self.modes_1).clear()

    def start(self):
        if self.first.selected == self.second.selected:
            self.error.text = "Выберите двух разных игроков."
            return
        by_id = {u["id"]: u for u in self.users}
        duel = Duel([by_id[self.first.selected], by_id[self.second.selected]],
                    self.mode, self.level.selected)
        self.navigate("duel_start", duel=duel)


class DuelPassScreen(BaseScreen):
    """Между ходами: «Ход переходит к ...» - передайте мышь второму игроку."""

    def __init__(self, manager, duel):
        super().__init__(manager)
        player = duel.current_player
        self.own(FloatingCubes())
        self.own(label("Первый игрок закончил", (0, 0.3), 0.9, mode_color(duel.mode),
                       origin=(0, 0)))
        self.own(Avatar(player["name"], player["color"], (0, 0.15), size=0.12))
        self.own(label(f"Ход переходит к игроку «{player['name']}»", (0, 0.02), 1.6, "strong",
                       origin=(0, 0)))
        self.own(label("Передайте мышь и клавиатуру. Задания будут те же самые.", (0, -0.05),
                       0.9, "muted", origin=(0, 0)))
        self.own(UIButton("Начать", lambda: self.navigate("duel_continue", duel=duel),
                          position=(0, -0.17), scale=(0.26, 0.07), variant="primary"))


class DuelResultsScreen(BaseScreen):
    """Итоги дуэли: оба игрока рядом и победитель."""

    def __init__(self, manager, duel):
        super().__init__(manager)
        self.own(FloatingCubes())
        accent = mode_color(duel.mode)
        winner = duel.winner()
        self.own(label(f"Итоги дуэли  •  {settings.MODE_NAMES[duel.mode]}", (0, 0.42), 0.9,
                       accent, origin=(0, 0)))
        title = ("Ничья!" if winner is None
                 else f"Победа: {duel.players[winner]['name']}")
        self.own(label(title, (0, 0.35), 2.2, "strong", origin=(0, 0)))

        for i, (player, session) in enumerate(zip(duel.players, duel.sessions)):
            x = -0.3 if i == 0 else 0.3
            self.own(Panel(0.5, 0.5, position=(x, 0.0),
                           border=GOLD if winner == i else settings.BORDER))
            self.own(Avatar(player["name"], player["color"], (x, 0.17), size=0.09))
            self.own(label(player["name"], (x, 0.09), 1.4, "strong", origin=(0, 0)))
            lines = [f"Верно: {session.correct} из {session.total}",
                     f"Баллы: {session.points}",
                     f"Время: {format_duration(session.total_time)}"]
            for k, line in enumerate(lines):
                self.own(label(line, (x, 0.0 - k * 0.055), 1.05, "text", origin=(0, 0)))
            if winner == i:
                self.own(label("победитель", (x, -0.2), 0.9, GOLD, origin=(0, 0)))

        self.own(UIButton("Реванш", lambda: self.navigate("duel_start", duel=duel.rematch()),
                          position=(-0.13, -0.38), scale=(0.24, 0.065), variant="primary"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(0.13, -0.38), scale=(0.24, 0.065)))
        self.own(label("Реванш - новые задания, первым ходит второй игрок", (0, -0.45), 0.75,
                       "muted", origin=(0, 0)))
