from ursina import *

from core import settings
from data.statistics import summarize
from engine.backdrop import FloatingCubes
from engine.objects import ColoredCube
from interface.base_screen import BaseScreen
from interface.ui_kit import label, LogoMark, ModeCard, Segmented, UIButton, StatTile

LEVELS = [("easy", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")]

# Режимы: (номер, ключ, название, описание)
MODES = [
    ("01", "rotation", "Вращение куба", "Какая грань окажется сверху"),
    ("02", "matching", "Одинаковые фигуры", "Найдите фигуру после поворота"),
    ("03", "projection", "Проекции", "Как фигура выглядит с разных сторон"),
]

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
        self.own(FloatingCubes())

        self.own(LogoMark((COLUMN_LEFT + 0.022, 0.4)))
        self.own(label("Тренажёр пространственного мышления",
                       (COLUMN_LEFT + 0.06, 0.4), 0.9, "accent"))
        self.own(label("Spatial Trainer 3D", (COLUMN_LEFT, 0.335), 2.6, "strong"))

        for i, (number, mode, title, subtitle) in enumerate(MODES):
            self.own(ModeCard(number, title, subtitle, mode,
                              lambda m=mode: self.start(m),
                              position=(COLUMN_CENTER, 0.2 - i * 0.12),
                              width=COLUMN_WIDTH, appear_delay=0.08 * i))

        self.own(label("Сложность", (COLUMN_LEFT, -0.135), 0.8, "muted"))
        self.own(Segmented(LEVELS, self.level, self.set_level,
                           position=(COLUMN_CENTER, -0.18), width=COLUMN_WIDTH))

        self.own(UIButton("Статистика", lambda: self.navigate("statistics"),
                          position=(COLUMN_LEFT + 0.11, -0.28), scale=(0.22, 0.06)))
        self.own(UIButton("Выход", application.quit, variant="ghost",
                          position=(COLUMN_LEFT + 0.31, -0.28), scale=(0.15, 0.06)))

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
