from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.backdrop import FloatingCubes
from interface.achievements_screen import AchievementToast
from interface.base_screen import BaseScreen
from interface.ui_kit import FRONT, label, mode_color, Panel, StatTile, UIButton
from logic.session import format_duration


class CustomResultsScreen(BaseScreen):
    """Итоги «Моей тренировки»: общие показатели и разбивка по режимам.
    saved=False, если результат не удалось сохранить."""

    def __init__(self, manager, playlist, saved=True, achievements=()):
        super().__init__(manager)
        if achievements:          # новые достижения за эту тренировку
            self.own(AchievementToast(achievements))
        accent = mode_color("custom")
        self.own(FloatingCubes())

        self.own(label("Моя тренировка завершена", (0, 0.42), 0.9, accent, origin=(0, 0)))
        self.own(label(f"{playlist.accuracy:.0f}%", (0, 0.33), 4, accent, origin=(0, 0)))
        self.own(label("точность", (0, 0.265), 0.85, "muted", origin=(0, 0)))

        total = len(playlist.all_results)
        tiles = [("Верно", f"{playlist.correct} из {total}"), ("Баллы", str(playlist.points)),
                 ("Общее время", format_duration(playlist.total_time))]
        width, gap = 0.24, 0.02
        start = -(len(tiles) * width + (len(tiles) - 1) * gap) / 2 + width / 2
        for i, (caption, value) in enumerate(tiles):
            self.own(StatTile(caption, value, (start + i * (width + gap), 0.17), width=width))

        # Разбивка по режимам
        merged = playlist.merged_by_mode()
        height = 0.05 + 0.045 * len(merged)
        top = 0.08
        self.own(Panel(0.78, height, position=(0, top - height / 2)))
        for i, session in enumerate(merged):
            y = top - 0.045 - i * 0.045
            color_hex = mode_color(session.mode)
            self.own(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                            position=(-0.36, y, FRONT), scale=(0.008, 0.026),
                            color=color.hex(color_hex)))
            self.own(label(settings.MODE_NAMES[session.mode], (-0.34, y), 0.95, "strong"))
            self.own(label(f"{session.correct}/{session.total}", (0.05, y), 0.95))
            self.own(label(f"{session.accuracy:.0f}%", (0.17, y), 0.95, color_hex))
            self.own(label(f"{session.points} б.", (0.36, y), 0.95, "text", origin=(0.5, 0)))

        # Ряд квадратиков по заданиям, под каждым - полоска цвета режима
        strip_y = top - height - 0.06
        results = [(s.mode, r) for s in playlist.sessions for r in s.results]
        size, gap = min(0.03, 1.0 / max(1, len(results)) - 0.006), 0.006
        start = -(len(results) * size + (len(results) - 1) * gap) / 2 + size / 2
        for i, (mode, result) in enumerate(results):
            x = start + i * (size + gap)
            hex_color = settings.CORRECT_COLOR if result.correct else settings.WRONG_COLOR
            self.own(Entity(parent=camera.ui, model=Quad(radius=0.2), shader=unlit_shader,
                            position=(x, strip_y, FRONT), scale=size, color=color.hex(hex_color)))
            self.own(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                            position=(x, strip_y - size / 2 - 0.008, FRONT),
                            scale=(size, 0.005), color=color.hex(mode_color(mode))))

        if playlist.adaptive:
            path = []
            for r in playlist.all_results:
                if not path or path[-1] != r.level:
                    path.append(r.level)
            text = "  ›  ".join(settings.LEVEL_NAMES[lvl] for lvl in path)
            self.own(label(f"Уровень по ходу тренировки:  {text}", (0, strip_y - 0.055), 0.85,
                           "muted", origin=(0, 0)))

        self.own(UIButton("Ещё раз", lambda: self.navigate("custom"),
                          position=(-0.13, -0.38), scale=(0.24, 0.065), variant="primary"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(0.13, -0.38), scale=(0.24, 0.065)))
        if not saved:
            self.own(label("Не удалось сохранить результат в базу данных.",
                           (0, -0.44), 0.85, "wrong", origin=(0, 0)))
        else:
            self.own(label("Баллы отражают результат в этой игре и не являются "
                           "измерением когнитивных способностей.",
                           (0, -0.45), 0.75, "muted", origin=(0, 0)))
