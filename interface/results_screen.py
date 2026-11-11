from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from interface.base_screen import BaseScreen
from engine.backdrop import FloatingCubes
from interface.ui_kit import FRONT, label, mode_color, StatTile, UIButton
from logic.session import format_duration


class ResultsScreen(BaseScreen):
    """Итоги тренировки. saved=False, если результат не удалось сохранить."""

    def __init__(self, manager, session, saved=True):
        super().__init__(manager)
        s = session
        accent = mode_color(s.mode)
        self.own(FloatingCubes())

        self.own(label("Тренировка завершена", (0, 0.4), 0.9, accent, origin=(0, 0)))
        self.own(label(settings.MODE_NAMES[s.mode], (0, 0.35), 1.9, "strong",
                       origin=(0, 0)))
        if s.adaptive and len(s.levels_path) > 1:
            # Адаптивная сложность: показываем, как менялся уровень
            path = "  ›  ".join(settings.LEVEL_NAMES[lvl] for lvl in s.levels_path)
            level_text = f"Уровень по ходу тренировки:  {path}"
        else:
            level_text = f"{settings.LEVEL_NAMES[s.summary_level]} уровень"
        self.own(label(level_text, (0, 0.3), 0.9, "muted", origin=(0, 0)))

        # Главная цифра - точность
        self.own(label(f"{s.accuracy:.0f}%", (0, 0.19), 5, accent, origin=(0, 0)))
        self.own(label("точность", (0, 0.105), 0.9, "muted", origin=(0, 0)))

        tiles = [
            ("Верно", f"{s.correct} из {s.total}"),
            ("Баллы", str(s.points)),
            ("Общее время", format_duration(s.total_time)),
            ("Среднее на задание", f"{s.average_time:.1f} с"),
        ]
        width, gap = 0.24, 0.02
        start = -(len(tiles) * width + (len(tiles) - 1) * gap) / 2 + width / 2
        for i, (caption, value) in enumerate(tiles):
            self.own(StatTile(caption, value, (start + i * (width + gap), -0.02),
                              width=width))

        self._task_strip(s.results, -0.13)

        self.own(UIButton("Тренироваться ещё", lambda: self.navigate(s.mode, level=s.level),
                          position=(-0.13, -0.26), scale=(0.24, 0.065), variant="primary"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(0.13, -0.26), scale=(0.24, 0.065)))

        if s.code:
            caption = ("Тренировка по коду" if s.locked else "Код этой тренировки")
            self.own(label(f"{caption}:  {s.code}", (0, -0.335), 1.0, accent, origin=(0, 0)))
            self.own(label("Друг, введя его в меню («По коду»), получит те же задания",
                           (0, -0.37), 0.75, "muted", origin=(0, 0)))

        if not saved:
            self.own(label("Не удалось сохранить результат в базу данных.",
                           (0, -0.405), 0.9, "wrong", origin=(0, 0)))

        self.own(label("Баллы отражают результат в этой игре и не являются "
                       "измерением когнитивных способностей.",
                       (0, -0.45), 0.8, "muted", origin=(0, 0)))

    def _task_strip(self, results, y):
        """Ряд квадратиков: каждое задание - зелёный (верно) или красный."""
        self.own(label("По заданиям", (0, y + 0.04), 0.8, "muted", origin=(0, 0)))
        size, gap = 0.03, 0.008
        start = -(len(results) * size + (len(results) - 1) * gap) / 2 + size / 2
        for i, result in enumerate(results):
            hex_color = settings.CORRECT_COLOR if result.correct else settings.WRONG_COLOR
            self.own(Entity(parent=camera.ui, model=Quad(radius=0.2), shader=unlit_shader,
                            position=(start + i * (size + gap), y, FRONT),
                            scale=size, color=color.hex(hex_color)))
