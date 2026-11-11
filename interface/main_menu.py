from ursina import *

from core import settings
from data.statistics import summarize
from engine.objects import ColoredCube
from interface.base_screen import BaseScreen
from interface.ui_kit import label, ModeCard, Segmented, UIButton, StatTile

LEVELS = [("easy", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")]

# Левая колонка меню: левый край и центр
COLUMN_LEFT = -0.74
COLUMN_WIDTH = 0.62
COLUMN_CENTER = COLUMN_LEFT + COLUMN_WIDTH / 2


class MainMenu(BaseScreen):
    """Главное меню: слева режимы и сложность, справа вращающийся куб
    и краткая сводка. history - список тренировок из базы или None."""

    # Выбранная сложность запоминается между заходами в меню
    remembered_level = "easy"

    def __init__(self, manager, history=None):
        super().__init__(manager)
        self.level = MainMenu.remembered_level

        self.own(label("Тренажёр пространственного мышления",
                       (COLUMN_LEFT, 0.37), 0.95, "accent"))
        self.own(label("Spatial Trainer 3D", (COLUMN_LEFT, 0.31), 2.5, "strong"))

        self.own(ModeCard("Вращение куба", "Какая грань окажется сверху",
                          "rotation", lambda: self.start("rotation"),
                          position=(COLUMN_CENTER, 0.17), width=COLUMN_WIDTH))
        self.own(ModeCard("Одинаковые фигуры", "Найдите фигуру после поворота",
                          "matching", lambda: self.start("matching"),
                          position=(COLUMN_CENTER, 0.035), width=COLUMN_WIDTH))

        self.own(label("Сложность", (COLUMN_LEFT, -0.075), 0.85, "muted"))
        self.own(Segmented(LEVELS, self.level, self.set_level,
                           position=(COLUMN_CENTER, -0.125), width=COLUMN_WIDTH))

        self.own(UIButton("Статистика", lambda: self.navigate("statistics"),
                          position=(COLUMN_LEFT + 0.11, -0.235), scale=(0.22, 0.06)))
        self.own(UIButton("Выход", application.quit, variant="ghost",
                          position=(COLUMN_LEFT + 0.31, -0.235), scale=(0.15, 0.06)))

        # Справа - медленно вращающийся куб (3D-объект в сцене)
        self.cube = self.own(ColoredCube(position=(3.7, 0.9, 0), scale=2.3))
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
        self.cube.rotation_y += 18 * time.dt

    def set_level(self, level):
        self.level = level
        MainMenu.remembered_level = level

    def start(self, mode):
        self.navigate(mode, level=self.level)
