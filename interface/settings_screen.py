from ursina import *

from core.preferences import prefs
from engine.backdrop import FloatingCubes
from engine.objects import ColoredCube, dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import label, Segmented, UIButton

LABEL_X = -0.8          # левый край подписей
CONTROL_X = -0.17       # центр переключателей
CONTROL_WIDTH = 0.62

# Разделы настроек: (заголовок, [(подпись, ключ настройки, [(значение, текст), ...])])
SECTIONS = [
    ("Куб", [
        ("Вид граней", "cube_skin",
         [("classic", "Цвета"), ("colorblind", "Для дальтоников"), ("dice", "Кость")]),
        ("Буквы на гранях", "face_marks", [(False, "Выкл"), (True, "Вкл")]),
    ]),
    ("Тренировка", [
        ("Заданий в тренировке", "session_length",
         [(5, "5"), (10, "10"), (15, "15"), (20, "20")]),
    ]),
    ("Управление", [
        ("Чувствительность мыши", "mouse_sensitivity",
         [("low", "Низкая"), ("medium", "Средняя"), ("high", "Высокая")]),
    ]),
    ("Комфорт", [
        ("Анимации и фон", "reduce_motion",
         [(False, "Полные"), (True, "Меньше движения")]),
    ]),
]


class SettingsScreen(BaseScreen):
    """Личные настройки игрока. on_change(ключ, значение) сохраняет настройку.
    Справа - куб, который сразу показывает выбранный вид граней."""

    def __init__(self, manager, player_name, on_change):
        super().__init__(manager)
        self.on_change = on_change
        self.preview = None
        self.own(FloatingCubes())

        right = window.top_right.x - 0.05
        self.own(label("Настройки", (LABEL_X, 0.42), 2.0, "strong"))
        self.own(label(f"Сохраняются для игрока «{player_name}»", (LABEL_X, 0.365),
                       0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06),
                          variant="ghost"))

        y = 0.29
        for title, rows in SECTIONS:
            self.own(label(title, (LABEL_X, y), 0.8, "accent"))
            y -= 0.06
            for caption, key, options in rows:
                self.own(label(caption, (LABEL_X, y), 0.9))
                self.own(Segmented(options, prefs.get(key),
                                   lambda value, k=key: self.change(k, value),
                                   position=(CONTROL_X, y), width=CONTROL_WIDTH,
                                   text_size=0.8))
                y -= 0.075
            y -= 0.015

        self.own(label("Так будет выглядеть куб", (0.48, -0.25), 0.85, "muted",
                       origin=(0, 0)))
        self._build_preview()

    def _build_preview(self):
        if self.preview:
            dispose(self.preview)
        self.preview = ColoredCube(skin=prefs.get("cube_skin"),
                                   marks=prefs.get("face_marks"),
                                   position=(4.1, 0.6, 0), scale=2.4)
        self.preview.rotation = (-22, 35, 0)

    def change(self, key, value):
        self.on_change(key, value)
        if key in ("cube_skin", "face_marks"):
            angle = self.preview.rotation_y
            self._build_preview()
            self.preview.rotation_y = angle

    def update(self):
        if self.preview and not prefs.reduce_motion:
            self.preview.rotation_y += 20 * time.dt

    def close(self):
        if self.preview:
            dispose(self.preview)
            self.preview = None
        super().close()
