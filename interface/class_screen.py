"""Экран «Задание для класса»: создать код с ограничением по времени и
посмотреть общую таблицу результатов по нему."""

from ursina import *

from core import settings
from engine.backdrop import FloatingCubes
from engine.objects import dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import label, Panel, Segmented, UIButton
from logic.class_tasks import TIME_LIMITS, results_for

MODE_ROWS = [
    [("rotation", "Вращение"), ("matching", "Фигуры"), ("projection", "Проекции"),
     ("construction", "Сборка"), ("nets", "Развёртка")],
    [("sections", "Сечения"), ("count", "Кубики"), ("memory", "Память"), ("shadow", "Тень"),
     ("reverse", "Повороты")],
    [("symmetry", "Симметрия"), ("views", "По видам"), ("changed", "Что изм."),
     ("observer", "Взгляд"), ("blitz", "Блиц")],
]
LEVELS = [("easy", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")]
LEFT_X = -0.42
RIGHT_X = 0.45
MAX_ROWS = 6


class ClassTaskScreen(BaseScreen):
    """assignments - созданные задания (новые первыми), players - [(имя, история)],
    on_create(режим, уровень, минут) -> новый список заданий,
    on_export(код) -> сообщение о сохранённой таблице."""

    def __init__(self, manager, assignments, players, on_create, on_export):
        super().__init__(manager)
        self.assignments = list(assignments or [])
        self.players = players or []
        self.on_create = on_create
        self.on_export = on_export
        self.selected = self.assignments[0]["code"] if self.assignments else None
        self.dynamic = []                 # список заданий и таблица (пересоздаются)
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(FloatingCubes())
        self.own(label("Задание для класса", (left, 0.42), 2.0, "strong"))
        self.own(label("Все решают одни и те же задания по коду - каждый в своём профиле",
                       (left, 0.365), 0.85, "muted"))
        self.own(UIButton("Назад", lambda: self.navigate("profiles"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06), variant="ghost"))

        # ---------- слева: создать задание ----------
        self.own(Panel(0.86, 0.74, position=(LEFT_X, -0.06)))
        x0 = LEFT_X - 0.4
        self.own(label("Режим", (x0, 0.27), 0.85, "muted"))
        self.mode = "rotation"
        self.mode_rows = []
        for i, row in enumerate(MODE_ROWS):
            switch = self.own(Segmented(row, "rotation" if i == 0 else None, self._mode,
                                        position=(LEFT_X, 0.225 - i * 0.06), width=0.8,
                                        text_size=0.72, height=0.05))
            if i:
                switch.clear()
            self.mode_rows.append(switch)
        self.own(label("Уровень", (x0, 0.02), 0.85, "muted"))
        self.level = self.own(Segmented(LEVELS, "easy", lambda _: None,
                                        position=(LEFT_X, -0.025), width=0.8, text_size=0.8))
        self.own(label("Время на всё задание", (x0, -0.085), 0.85, "muted"))
        self.minutes = self.own(Segmented(
            [(m, f"{m} мин" if m else "без ограничения") for m in TIME_LIMITS], 10,
            lambda _: None, position=(LEFT_X, -0.13), width=0.8, text_size=0.75))
        self.own(UIButton("Создать код", self.create, position=(LEFT_X, -0.215),
                          scale=(0.4, 0.06), variant="primary"))
        self.code_text = self.own(label("", (LEFT_X, -0.3), 2.2, "accent", origin=(0, 0)))
        self.code_note = self.own(label("", (LEFT_X, -0.37), 0.72, "muted", origin=(0, 0)))

        # ---------- справа: результаты ----------
        self.own(Panel(0.8, 0.74, position=(RIGHT_X, -0.06)))
        self.own(label("Результаты", (RIGHT_X - 0.37, 0.27), 0.85, "muted"))
        self.export_note = self.own(label("", (RIGHT_X, -0.39), 0.7, "muted", origin=(0, 0)))
        self.export_button = self.own(UIButton("Сохранить таблицу (CSV)", self.export,
                                               position=(RIGHT_X, -0.34), scale=(0.4, 0.05),
                                               text_size=0.75))
        self._refresh()

    def _mode(self, mode):
        self.mode = mode
        for row, switch in zip(MODE_ROWS, self.mode_rows):
            if mode not in dict(row):
                switch.clear()

    def create(self):
        self.assignments = self.on_create(self.mode, self.level.selected,
                                          self.minutes.selected)
        new = self.assignments[0]
        self.selected = new["code"]
        self.code_text.text = new["code"]
        limit = f", на всё {new['minutes']} мин" if new["minutes"] else ""
        self.code_note.text = (f"{settings.MODE_NAMES[new['mode']]}{limit}. Ученик: «Игроки» - "
                               "выбрать себя - в меню «По коду»")
        self._refresh()

    def select(self, code):
        self.selected = code
        self.export_note.text = ""
        self._refresh()

    def export(self):
        if self.selected:
            self.export_note.text = self.on_export(self.selected)

    def _refresh(self):
        for obj in self.dynamic:
            dispose(obj)
        self.dynamic = []
        if not self.assignments:
            self.dynamic.append(label("Пока нет заданий. Создайте код слева.",
                                      (RIGHT_X, 0.05), 0.9, "muted", origin=(0, 0)))
            self.export_button.enabled = False
            return
        self.export_button.enabled = True
        # Последние задания - кнопками
        for i, item in enumerate(self.assignments[:4]):
            chosen = item["code"] == self.selected
            self.dynamic.append(UIButton(
                f"{item['code']}  {settings.MODE_NAMES[item['mode']][:12]}",
                lambda c=item["code"]: self.select(c),
                position=(RIGHT_X - 0.19 + (i % 2) * 0.38, 0.22 - (i // 2) * 0.06),
                scale=(0.36, 0.05), text_size=0.7,
                variant="primary" if chosen else "secondary"))
        rows = results_for(self.selected, self.players)
        columns = [("Игрок", -0.36, (-0.5, 0)), ("Верно", 0.02, (0.5, 0)),
                   ("Точность, %", 0.17, (0.5, 0)), ("Время, с", 0.33, (0.5, 0))]
        for title, dx, origin in columns:
            self.dynamic.append(label(title.replace(", %", "").replace(", с", ""),
                                      (RIGHT_X + dx, 0.11), 0.75, "muted", origin=origin))
        if not rows:
            self.dynamic.append(label("По этому коду ещё никто не решал.", (RIGHT_X, 0.0),
                                      0.85, "muted", origin=(0, 0)))
        for n, row in enumerate(rows[:MAX_ROWS]):
            y = 0.06 - n * 0.055
            values = [row["Игрок"], f"{row['Верно']} из {row['Заданий']}",
                      f"{row['Точность, %']}%", str(row["Время, с"])]
            for value, (_, dx, origin) in zip(values, columns):
                self.dynamic.append(label(value, (RIGHT_X + dx, y), 0.9,
                                          "accent" if n == 0 else "text", origin=origin))

    def close(self):
        for obj in self.dynamic:
            dispose(obj)
        self.dynamic = []
        super().close()
