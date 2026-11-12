from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from data.statistics import filter_history, progress_series, compare_recent
from engine.objects import dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import FRONT, label, Panel, Segmented, UIButton

# Режимы в два ряда: десять кнопок в один ряд не помещаются
MODES_ROW_1 = [(None, "Все"), ("rotation", "Вращение"), ("matching", "Фигуры"),
               ("projection", "Проекции"), ("construction", "Сборка"), ("nets", "Развёртка")]
MODES_ROW_2 = [("sections", "Сечения"), ("count", "Кубики"), ("memory", "Память"),
               ("shadow", "Тень"), ("reverse", "Повороты")]
MODES_ROW_3 = [("symmetry", "Симметрия"), ("views", "Виды"), ("changed", "Что изм."),
               ("observer", "Взгляд"), ("blitz", "Блиц")]
MODES = MODES_ROW_1 + MODES_ROW_2 + MODES_ROW_3
LEVELS = [(None, "Все"), ("easy", "Начальный"), ("medium", "Средний"),
          ("hard", "Продвинутый")]

CHART_LEFT = -0.68
CHART_WIDTH = 1.4
CHART_BOTTOM = -0.27
CHART_HEIGHT = 0.3
MAX_BARS = 12


class ProgressScreen(BaseScreen):
    """График точности по тренировкам. history: список словарей или None."""

    def __init__(self, manager, history):
        super().__init__(manager)
        self.history = history
        self.mode = None
        self.level = None
        # Все элементы графика - дети одного контейнера. Контейнер принадлежит
        # экрану (own), поэтому при выходе удаляется вместе со всем графиком.
        self.chart = self.own(Entity(parent=camera.ui))

        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(label("Прогресс", (left, 0.42), 2.0, "strong"))
        self.own(label("Точность по последним тренировкам", (left, 0.365), 0.85, "muted"))
        self.own(UIButton("Статистика", lambda: self.navigate("statistics"),
                          position=(right - 0.32, 0.42), scale=(0.2, 0.06)))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06),
                          variant="ghost"))
        self.own(label("Показатели отражают результаты в игре и не доказывают "
                       "изменения когнитивных способностей.",
                       (0, -0.45), 0.8, "muted", origin=(0, 0)))

        if history is None:
            self.own(label("Не удалось прочитать данные из базы.", (0, 0), 1.0,
                           "wrong", origin=(0, 0)))
            return

        self.own(label("Режим", (-0.81, 0.27), 0.8, "muted"))
        self.mode_switch = self.own(Segmented(MODES_ROW_1, None, self.set_mode,
                                              position=(-0.42, 0.235), width=0.78,
                                              text_size=0.75, height=0.05))
        self.mode_switch_2 = self.own(Segmented(MODES_ROW_2, None, self.set_mode,
                                                position=(-0.42, 0.18), width=0.78,
                                                text_size=0.75, height=0.05))
        self.mode_switch_2.clear()
        # Третий ряд режимов - справа, под выбором уровня
        self.mode_switch_3 = self.own(Segmented(MODES_ROW_3, None, self.set_mode,
                                                position=(0.42, 0.18), width=0.78,
                                                text_size=0.75, height=0.05))
        self.mode_switch_3.clear()
        self.own(label("Уровень", (0.03, 0.27), 0.8, "muted"))
        self.level_switch = self.own(Segmented(LEVELS, None, self.set_level,
                                               position=(0.42, 0.235), width=0.78,
                                               text_size=0.8))
        self.own(Panel(1.62, 0.5, position=(0, -0.1)))
        self.refresh()

    # ---------- фильтры ----------
    def set_mode(self, mode):
        self.mode = mode
        # Выбор в одном ряду снимает выделение в других
        for row, switch in self._rows():
            if mode not in dict(row):
                switch.clear()
        self.refresh()

    def _rows(self):
        return ((MODES_ROW_1, self.mode_switch), (MODES_ROW_2, self.mode_switch_2),
                (MODES_ROW_3, self.mode_switch_3))

    def set_level(self, level):
        self.level = level
        self.refresh()

    def next_mode(self):
        keys = [key for key, _ in MODES]
        mode = keys[(keys.index(self.mode) + 1) % len(keys)]
        switch = next(s for row, s in self._rows() if mode in dict(row))
        switch.select(mode)

    def next_level(self):
        keys = [key for key, _ in LEVELS]
        self.level_switch.select(keys[(keys.index(self.level) + 1) % len(keys)])

    # ---------- график ----------
    def _chart_text(self, text, position, size=1.0, tone="text", origin=(0, 0)):
        label(text, position, size, tone, origin=origin, parent=self.chart)

    def _chart_rect(self, center_x, y, width, height, hex_color, bottom_origin=False,
                    z=FRONT / 2):
        Entity(parent=self.chart, model="quad", shader=unlit_shader,
               origin=(0, -0.5) if bottom_origin else (0, 0),
               position=(center_x, y, z), scale=(width, height),
               color=color.hex(hex_color))

    def refresh(self):
        # Стираем старый график, сам контейнер оставляем
        for obj in list(self.chart.children):
            dispose(obj)

        subset = filter_history(self.history, self.mode, self.level)
        series = progress_series(subset, MAX_BARS)
        if not series:
            self._chart_text("Нет тренировок с такими настройками.", (0, -0.1), 1.0, "muted")
            return

        self._chart_text(f"Точность, %  •  последние {len(series)}", (CHART_LEFT, 0.11),
                         0.8, "muted", origin=(-0.5, 0))

        # Линии сетки: 0%, 50%, 100% с подписями
        for percent in (0, 50, 100):
            y = CHART_BOTTOM + CHART_HEIGHT * percent / 100
            self._chart_rect(CHART_LEFT + CHART_WIDTH / 2, y, CHART_WIDTH, 0.0015,
                             settings.BORDER, z=FRONT / 4)   # сетка - позади столбцов
            self._chart_text(f"{percent}", (CHART_LEFT - 0.035, y), 0.75, "muted")

        # Столбцы: последний (самый новый) - ярким акцентом, остальные приглушённее
        slot = CHART_WIDTH / MAX_BARS
        for i, value in enumerate(series):
            x = CHART_LEFT + slot * (i + 0.5)
            height = max(0.004, CHART_HEIGHT * value / 100)
            newest = i == len(series) - 1
            self._chart_rect(x, CHART_BOTTOM, slot * 0.55, height,
                             settings.ACCENT if newest else settings.SELECTED_COLOR,
                             bottom_origin=True)
            self._chart_text(f"{value:.0f}", (x, CHART_BOTTOM + height + 0.022), 0.75,
                             "strong" if newest else "text")

        self._chart_text("старые  ›  новые", (0, CHART_BOTTOM - 0.035), 0.75, "muted")

        # Сравнение последних тренировок с более ранними
        comparison = compare_recent(subset, 3)
        if comparison is None:
            text = "Для сравнения нужно больше 3 тренировок с выбранными настройками."
        else:
            text = (f"Последние {comparison['recent_count']}: "
                    f"{comparison['recent_accuracy']:.0f}%   •   "
                    f"более ранние ({comparison['earlier_count']}): "
                    f"{comparison['earlier_accuracy']:.0f}%   •   "
                    f"разница {comparison['difference']:+.0f} п.п.")
        self._chart_text(text, (0, -0.39), 0.9)
