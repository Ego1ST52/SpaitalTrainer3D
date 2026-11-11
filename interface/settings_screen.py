from ursina import *

from core.preferences import prefs
from engine.backdrop import FloatingCubes
from engine.objects import ColoredCube, dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import label, Segmented, UIButton
from logic.achievements import BY_KEY, SKIN_UNLOCKS
from logic.cube_skins import SKINS

LABEL_X = -0.8          # левый край подписей
CONTROL_X = -0.17       # центр переключателей
CONTROL_WIDTH = 0.62

# Разделы настроек: (заголовок, [(подпись, ключ настройки, [(значение, текст), ...])])
SECTIONS = [
    ("Куб", [
        ("Вид граней", "cube_skin", None),        # сетка скинов, см. _build_skin_picker
        ("Буквы на гранях", "face_marks", [(False, "Выкл"), (True, "Вкл")]),
    ]),
    ("Тренировка", [
        ("Заданий в тренировке", "session_length",
         [(5, "5"), (10, "10"), (15, "15"), (20, "20")]),
        ("Адаптивная сложность", "adaptive", [(False, "Выкл"), (True, "Вкл")]),
        ("Вращать куб до ответа", "free_rotation",
         [(False, "Только после"), (True, "Всегда")]),
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

    def __init__(self, manager, player_name, on_change, unlocked_skins=()):
        super().__init__(manager)
        self.on_change = on_change
        self.unlocked_skins = set(unlocked_skins)
        self.skin_buttons = {}
        self.preview = None
        self.own(FloatingCubes())

        right = window.top_right.x - 0.05
        self.own(label("Настройки", (LABEL_X, 0.42), 2.0, "strong"))
        self.own(label(f"Сохраняются для игрока «{player_name}»", (LABEL_X, 0.365),
                       0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06),
                          variant="ghost"))

        y = 0.3
        for title, rows in SECTIONS:
            self.own(label(title, (LABEL_X, y), 0.8, "accent"))
            y -= 0.055
            for caption, key, options in rows:
                self.own(label(caption, (LABEL_X, y), 0.9))
                if options is None:
                    y = self._build_skin_picker(y)
                    continue
                self.own(Segmented(options, prefs.get(key),
                                   lambda value, k=key: self.change(k, value),
                                   position=(CONTROL_X, y), width=CONTROL_WIDTH,
                                   text_size=0.8))
                y -= 0.064
            y -= 0.012

        self.own(label("Так будет выглядеть куб", (0.48, -0.25), 0.85, "muted",
                       origin=(0, 0)))
        self._build_preview()

    def _build_skin_picker(self, y):
        """Шесть скинов в два ряда. Скины-награды закрыты, пока не получено
        достижение; клик по закрытому подсказывает, какое именно."""
        pad, columns = 0.01, 3
        chip = (CONTROL_WIDTH - pad * (columns - 1)) / columns
        for i, skin in enumerate(SKINS):
            row, col = divmod(i, columns)
            x = CONTROL_X - CONTROL_WIDTH / 2 + chip / 2 + col * (chip + pad)
            self.skin_buttons[skin] = self.own(
                UIButton(SKINS[skin]["title"], lambda k=skin: self.pick_skin(k),
                         position=(x, y - row * 0.058), scale=(chip, 0.05), text_size=0.75))
        self.skin_hint = self.own(label("", (CONTROL_X - CONTROL_WIDTH / 2, y - 0.105), 0.7,
                                        "muted"))
        self._refresh_skins()
        return y - 0.15

    def _locked(self, skin):
        return skin in SKIN_UNLOCKS and skin not in self.unlocked_skins

    def _refresh_skins(self):
        current = prefs.get("cube_skin")
        for skin, button in self.skin_buttons.items():
            button.set_variant("primary" if skin == current
                               else "ghost" if self._locked(skin) else "secondary")
        locked = [SKINS[k]["title"] for k in SKINS if self._locked(k)]
        self.skin_hint.text = (f"закрыто: {', '.join(locked)} - открываются достижениями"
                               if locked else "все скины открыты")

    def pick_skin(self, skin):
        if self._locked(skin):
            achievement = BY_KEY[SKIN_UNLOCKS[skin]]
            self.skin_hint.text = (f"«{SKINS[skin]['title']}» откроется за достижение "
                                   f"«{achievement.title}»")
            return
        self.change("cube_skin", skin)
        self._refresh_skins()

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
