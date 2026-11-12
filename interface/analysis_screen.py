import textwrap

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from interface.base_screen import BaseScreen
from interface.ui_kit import FRONT, label, mode_color, Panel, UIButton
from logic.insights import MIN_SAMPLES, insights, practice_steps, tag_label, weakest_tags
from logic.playlist import Playlist

KIND_COLORS = {"weak": "WRONG_COLOR", "mistake": "#fbbf24", "strong": "CORRECT_COLOR",
               "info": "TEXT_MUTED"}
MAX_CARDS = 4


class AnalysisScreen(BaseScreen):
    """Персональные выводы по журналу заданий. log - список из
    Database.get_task_log() или None, если база недоступна."""

    def __init__(self, manager, log):
        super().__init__(manager)
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(label("Анализ ошибок", (left, 0.42), 2.0, "strong"))
        self.own(label("Что даётся труднее и почему - по вашим заданиям", (left, 0.365), 0.85,
                       "muted"))
        self.own(UIButton("Статистика", lambda: self.navigate("statistics"),
                          position=(right - 0.32, 0.42), scale=(0.2, 0.06)))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06), variant="ghost"))

        if log is None:
            self.own(label("Не удалось прочитать данные из базы.", (0, 0.1), 1.0, "wrong",
                           origin=(0, 0)))
            return
        self._cards(insights(log)[:MAX_CARDS], left)
        self._hardest(log)
        self._practice(log, right)
        self.own(label("Выводы появляются, когда заданий одного типа набирается хотя бы "
                       f"{MIN_SAMPLES} - чтобы не судить по случайным ошибкам.",
                       (0, -0.455), 0.75, "muted", origin=(0, 0)))

    def _cards(self, found, left):
        width, height = 0.8, 0.14
        for i, insight in enumerate(found):
            y = 0.25 - i * (height + 0.025)
            center_x = left + width / 2
            self.own(Panel(width, height, position=(center_x, y)))
            hex_color = KIND_COLORS[insight.kind]
            hex_color = getattr(settings, hex_color, hex_color)
            self.own(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                            position=(left + 0.012, y, FRONT), scale=(0.006, height * 0.7),
                            color=color.hex(hex_color)))
            self.own(label(insight.title, (left + 0.03, y + 0.035), 0.95, "strong"))
            self.own(label(textwrap.fill(insight.detail, 68), (left + 0.03, y - 0.02), 0.75,
                           "text"))

    def _practice(self, log, right):
        """Кнопка «Работа над ошибками»: тренировка из самых трудных режимов."""
        steps = practice_steps(log)
        x = 0.06
        if not steps:
            self.own(label("Работа над ошибками появится, когда наберётся режим "
                           "с точностью ниже 90%.", (x, -0.39), 0.72, "muted"))
            return
        names = ", ".join(settings.MODE_NAMES[mode] for mode, _ in steps)
        self.own(label(textwrap.fill(f"Работа над ошибками: {names}", 52), (x, -0.335),
                       0.75, "text"))
        self.own(UIButton("Начать работу над ошибками", lambda: self.start_practice(steps),
                          position=(right - 0.2, -0.4), scale=(0.4, 0.06), variant="primary"))

    def start_practice(self, steps):
        # Адаптивная сложность: начинаем с простого, дальше - по ответам
        playlist = Playlist(steps, "easy", adaptive=True)
        self.navigate(steps[0][0], playlist=playlist)

    def _hardest(self, log):
        x = 0.06
        self.own(label("Самые трудные типы заданий", (x, 0.3), 0.85, "accent"))
        rows = weakest_tags(log)
        if not rows:
            self.own(label("Пока недостаточно заданий одного типа.", (x, 0.25), 0.8, "muted"))
            return
        bar_width = 0.32
        for i, (mode, tag, accuracy, count) in enumerate(rows):
            y = 0.245 - i * 0.07
            name = f"{settings.MODE_NAMES.get(mode, mode)}: {tag_label(tag)}"
            self.own(label(name, (x, y), 0.78, "text"))
            self.own(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                            origin=(-0.5, 0), position=(x, y - 0.03, FRONT),
                            scale=(bar_width, 0.01), color=color.hex(settings.BORDER)))
            if accuracy > 0:
                self.own(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                                origin=(-0.5, 0), position=(x, y - 0.03, FRONT * 1.5),
                                scale=(bar_width * accuracy / 100, 0.01),
                                color=color.hex(mode_color(mode))))
            self.own(label(f"{accuracy:.0f}%  ·  {count} зад.", (x + bar_width + 0.02, y - 0.03),
                           0.75, "muted"))
