from ursina import *

from core import settings
from data.statistics import summarize
from engine.backdrop import FloatingCubes
from core.preferences import prefs
from engine.objects import ColoredCube, dispose
from interface.base_screen import BaseScreen
from interface.code_dialog import CodeDialog
from interface.ui_kit import (label, LogoMark, ModeCard, PlayerChip, Segmented, UIButton,
                              StatTile)

LEVELS = [("easy", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")]

# Режимы: (номер, ключ, название, описание)
MODES = [
    ("01", "rotation", "Вращение куба", "Какая грань окажется сверху"),
    ("02", "matching", "Одинаковые фигуры", "Найдите фигуру после поворота"),
    ("03", "projection", "Проекции", "Как фигура выглядит с разных сторон"),
    ("04", "construction", "Конструирование", "Соберите фигуру из кубиков по образцу"),
]

# Левая колонка меню: левый край и центр
COLUMN_LEFT = -0.74
COLUMN_WIDTH = 0.62
COLUMN_CENTER = COLUMN_LEFT + COLUMN_WIDTH / 2


class MainMenu(BaseScreen):
    """Главное меню: слева режимы и сложность, справа вращающийся куб
    и краткая сводка. history - список тренировок из базы или None,
    player - текущий игрок {"name": ..., "color": ...}."""

    # Выбранная сложность запоминается между заходами в меню
    remembered_level = "easy"

    def __init__(self, manager, history=None, player=None):
        super().__init__(manager)
        self.level = MainMenu.remembered_level
        self.dialog = None
        self.own(FloatingCubes())

        if player:
            self.own(PlayerChip(player["name"], player["color"],
                                lambda: self.navigate("profiles"),
                                position=(window.top_right.x - 0.21, 0.41)))

        self.own(LogoMark((COLUMN_LEFT + 0.022, 0.4)))
        self.own(label("Тренажёр пространственного мышления",
                       (COLUMN_LEFT + 0.06, 0.4), 0.9, "accent"))
        self.own(label("Spatial Trainer 3D", (COLUMN_LEFT, 0.335), 2.6, "strong"))

        for i, (number, mode, title, subtitle) in enumerate(MODES):
            self.own(ModeCard(number, title, subtitle, mode,
                              lambda m=mode: self.start(m),
                              position=(COLUMN_CENTER, 0.215 - i * 0.108),
                              width=COLUMN_WIDTH, height=0.094, appear_delay=0.08 * i))

        self.own(label("Сложность", (COLUMN_LEFT, -0.19), 0.8, "muted"))
        self.own(Segmented(LEVELS, self.level, self.set_level,
                           position=(COLUMN_CENTER, -0.235), width=COLUMN_WIDTH))

        buttons = [("Статистика", lambda: self.navigate("statistics")),
                   ("Настройки", lambda: self.navigate("settings")),
                   ("По коду", self.open_code_dialog)]
        width = (COLUMN_WIDTH - 0.02) / len(buttons)
        for i, (text, action) in enumerate(buttons):
            self.own(UIButton(text, action, scale=(width, 0.06),
                              position=(COLUMN_LEFT + width / 2 + i * (width + 0.01), -0.33)))
        self.own(UIButton("Выход", application.quit, variant="ghost",
                          position=(COLUMN_LEFT + 0.06, -0.42), scale=(0.12, 0.05),
                          text_size=0.8))

        # Справа - медленно вращающийся куб в выбранном игроком виде
        self.cube = self.own(ColoredCube(skin=prefs.get("cube_skin"),
                                         marks=prefs.get("face_marks"),
                                         position=(3.7, 0.9, 0), scale=2.3))
        self.cube.rotation_x = -22
        self._summary(history)

    def _summary(self, history):
        if history:
            last = history[0]   # история отсортирована: новые первыми
            last_text = (f"{last['tasks_correct']}/{last['tasks_total']}"
                         f"  ·  {last['points']} б.")
            accuracy_text = f"{summarize(history)['accuracy']:.0f}%"
        else:
            last_text = accuracy_text = "—"
        self.own(StatTile("Последняя тренировка", last_text, (0.3, -0.27)))
        self.own(StatTile("Точность за всё время", accuracy_text, (0.58, -0.27),
                          tone="accent"))

    def update(self):
        if not prefs.reduce_motion:
            self.cube.rotation_y += 18 * time.dt

    def set_level(self, level):
        self.level = level
        MainMenu.remembered_level = level

    def start(self, mode):
        if self.dialog is None:
            self.navigate(mode, level=self.level)

    # ---------- тренировка по коду ----------
    def open_code_dialog(self):
        if self.dialog is None:
            self.dialog = CodeDialog(self.start_by_code, self.close_code_dialog)

    def close_code_dialog(self):
        if self.dialog is not None:
            dispose(self.dialog)
            self.dialog = None

    def start_by_code(self, mode, level, seed):
        self.close_code_dialog()
        self.navigate(mode, level=level, seed=seed, locked=True)

    def close(self):
        self.close_code_dialog()
        super().close()
