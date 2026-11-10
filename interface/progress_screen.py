from ursina import *

from core import settings
from data.statistics import filter_history, progress_series, compare_recent
from engine.objects import dispose
from interface.base_screen import BaseScreen

MODES = [None, "rotation", "matching"]
LEVELS = [None, "easy", "medium", "hard"]

CHART_LEFT = -0.55
CHART_WIDTH = 1.1
CHART_BOTTOM = -0.17
CHART_HEIGHT = 0.36
MAX_BARS = 12


class ProgressScreen(BaseScreen):
    """График точности по тренировкам. history: список словарей или None."""

    def __init__(self, manager, history):
        super().__init__(manager)
        self.history = history
        self.mode_index = 0
        self.level_index = 0
        self.chart_objects = []
        accent = color.hex(settings.ACCENT)

        self.own(Text("Прогресс", origin=(0, 0), position=(0, 0.4),
                      scale=2.2, color=accent))
        self._button("В меню", (0, -0.4), lambda: self.navigate("menu"), (0.3, 0.07))
        self.own(Text("Показатели отражают результаты в игре и не доказывают "
                      "изменения когнитивных способностей.",
                      origin=(0, 0), position=(0, -0.46), scale=0.9,
                      color=color.hex("#64748b")))

        if history is None:
            self.own(Text("Не удалось прочитать данные из базы.", origin=(0, 0),
                          position=(0, 0.1), scale=1.2,
                          color=color.hex(settings.WRONG_COLOR)))
            return

        self.mode_button = self._button("", (-0.3, 0.3), self.next_mode, (0.5, 0.07))
        self.level_button = self._button("", (0.3, 0.3), self.next_level, (0.5, 0.07))
        self.refresh()

    def _button(self, label, position, action, scale):
        button = Button(text=label, color=color.hex(settings.BUTTON_COLOR),
                        highlight_color=color.hex(settings.BUTTON_HOVER),
                        scale=scale, position=position)
        button.on_click = action
        return self.own(button)

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(MODES)
        self.refresh()

    def next_level(self):
        self.level_index = (self.level_index + 1) % len(LEVELS)
        self.refresh()

    def _chart_text(self, text, position, scale=1.0, text_color=None):
        obj = Text(text, origin=(0, 0), position=position, scale=scale,
                   color=text_color or color.hex(settings.TEXT_COLOR))
        self.chart_objects.append(obj)

    def _chart_rect(self, center_x, y, width, height, hex_color, bottom_origin=False):
        obj = Entity(parent=camera.ui, model="quad",
                     origin=(0, -0.5) if bottom_origin else (0, 0),
                     position=(center_x, y), scale=(width, height),
                     color=color.hex(hex_color))
        self.chart_objects.append(obj)

    def refresh(self):
        for obj in self.chart_objects:
            dispose(obj)
        self.chart_objects = []

        mode = MODES[self.mode_index]
        level = LEVELS[self.level_index]
        self.mode_button.text = "Режим: " + ("все" if mode is None
                                             else settings.MODE_NAMES[mode])
        self.level_button.text = "Уровень: " + ("все" if level is None
                                                else settings.LEVEL_NAMES[level])

        subset = filter_history(self.history, mode, level)
        series = progress_series(subset, MAX_BARS)
        if not series:
            self._chart_text("Нет тренировок с такими настройками.", (0, 0), 1.2)
            return

        self._chart_text(f"Точность по последним {len(series)} тренировкам, %",
                         (0, 0.22), 1.1)

        # Линии сетки: 0%, 50%, 100% с подписями
        for percent in (0, 50, 100):
            y = CHART_BOTTOM + CHART_HEIGHT * percent / 100
            self._chart_rect(CHART_LEFT + CHART_WIDTH / 2, y, CHART_WIDTH, 0.002, "#2b3e5a")
            self._chart_text(f"{percent}", (CHART_LEFT - 0.04, y), 0.9)

        # Столбцы
        slot = CHART_WIDTH / MAX_BARS
        for i, value in enumerate(series):
            x = CHART_LEFT + slot * (i + 0.5)
            height = max(0.004, CHART_HEIGHT * value / 100)
            self._chart_rect(x, CHART_BOTTOM, slot * 0.7, height,
                             settings.ACCENT, bottom_origin=True)
            self._chart_text(f"{value:.0f}", (x, CHART_BOTTOM + height + 0.025), 0.8)

        self._chart_text("старые  ->  новые", (0, CHART_BOTTOM - 0.04), 0.9,
                         color.hex("#64748b"))

        # Сравнение последних тренировок с более ранними
        comparison = compare_recent(subset, 3)
        if comparison is None:
            text = "Для сравнения нужно больше 3 тренировок с выбранными настройками."
        else:
            text = (f"Последние {comparison['recent_count']}: "
                    f"{comparison['recent_accuracy']:.0f}%.  "
                    f"Более ранние ({comparison['earlier_count']}): "
                    f"{comparison['earlier_accuracy']:.0f}%.  "
                    f"Разница: {comparison['difference']:+.0f} п.п.")
        self._chart_text(text, (0, -0.28), 1.1)