from ursina import *

from core.preferences import prefs
from engine.backdrop import FloatingCubes
from engine.objects import ColoredCube, dispose
from interface.base_screen import BaseScreen
from core import settings
from interface.ui_kit import FRONT, label, Segmented, UIButton
from logic.theme import PRESETS, parse_color
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
]

# Правая колонка, под темой интерфейса
RIGHT_X = 0.2
RIGHT_CONTROL_X = 0.66
RIGHT_WIDTH = 0.36
RIGHT_SECTIONS = [
    ("Комфорт", [
        ("Анимации и фон", "reduce_motion",
         [(False, "Полные"), (True, "Меньше")]),
        ("Звук", "sound", [("off", "Выкл"), ("quiet", "Тихо"), ("loud", "Громко")]),
        ("Стерео 3D (очки)", "stereo", [(False, "Выкл"), (True, "Красно-синие")]),
    ]),
]
STEREO_NOTE = "Стерео включится после перезапуска игры"


class SettingsScreen(BaseScreen):
    """Личные настройки игрока. on_change(ключ, значение) сохраняет настройку.
    Справа - куб, который сразу показывает выбранный вид граней."""

    def __init__(self, manager, player_name, on_change, unlocked_skins=(), on_theme=None):
        super().__init__(manager)
        self.on_change = on_change
        self.on_theme = on_theme
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

        self._build_rows(SECTIONS, 0.3, LABEL_X, CONTROL_X, CONTROL_WIDTH)
        self._build_theme_block()
        y = self._build_rows(RIGHT_SECTIONS, -0.0, RIGHT_X, RIGHT_CONTROL_X, RIGHT_WIDTH)
        self.stereo_note = self.own(label("", (RIGHT_X, y + 0.025), 0.75, "muted"))
        self.own(label("Так будет выглядеть куб", (0.3, -0.33), 0.8, "muted",
                       origin=(0, 0)))
        self._build_preview()

    # ---------- тема ----------
    def _build_theme_block(self):
        """Тема интерфейса: строка для цвета, «Применить», «Сброс» и готовые темы."""
        left = 0.2              # правее сетки скинов
        current = prefs.get("theme")
        self.own(label("Тема интерфейса", (left, 0.3), 0.8, "accent"))
        self.theme_field = self.own(InputField(position=(left + 0.15, 0.245, FRONT * 2),
                                               scale=(0.3, 0.055), character_limit=14,
                                               color=color.hex(settings.BUTTON_COLOR)))
        self.theme_field.text = current
        self.theme_field.submit_on = ["enter"]
        self.theme_field.on_submit = self.apply_typed_theme
        self.own(UIButton("Применить", self.apply_typed_theme, position=(left + 0.395, 0.245),
                          scale=(0.17, 0.055), variant="primary", text_size=0.8))
        self.own(UIButton("Сброс", lambda: self.set_theme(""), position=(left + 0.55, 0.245),
                          scale=(0.12, 0.055), variant="ghost", text_size=0.8))
        self.theme_hint = self.own(label("Любой цвет: #ff7a00, #f70 или словом: «мятный», "
                                         "«бордовый»", (left, 0.195), 0.7, "muted"))

        # Готовые темы - цветные кружки; у текущей - светлое кольцо
        for i, (name, hex_value) in enumerate(PRESETS):
            x = left + 0.022 + i * 0.066
            swatch = hex_value or "#22d3ee"            # стандартная тема - бирюзовая
            if hex_value == current:
                self.own(Entity(parent=camera.ui, model="circle", scale=0.054,
                                position=(x, 0.14, FRONT / 2),
                                color=color.hex(settings.TEXT_STRONG)))
            button = self.own(UIButton("", lambda c=hex_value: self.set_theme(c),
                                       position=(x, 0.14, FRONT), scale=(0.044, 0.044),
                                       radius=0.5))
            button.color = button.highlight_color = color.hex(swatch)
            button.model.setColorScale(button.color)
            self.own(label(name, (x, 0.098), 0.6, "muted", origin=(0, 0)))
        current_name = next((n for n, h in PRESETS if h == current), None)
        caption = (f"Сейчас: {current_name}" if current_name
                   else f"Сейчас: своя тема {current}")
        self.own(label(caption, (left, 0.055), 0.75, "text"))

    def _build_rows(self, sections, y, label_x, control_x, width):
        """Разделы с переключателями сверху вниз. Возвращает y под ними."""
        for title, rows in sections:
            self.own(label(title, (label_x, y), 0.8, "accent"))
            y -= 0.055
            for caption, key, options in rows:
                self.own(label(caption, (label_x, y), 0.9))
                if options is None:
                    y = self._build_skin_picker(y)
                    continue
                self.own(Segmented(options, prefs.get(key),
                                   lambda value, k=key: self.change(k, value),
                                   position=(control_x, y), width=width, text_size=0.8))
                y -= 0.064
            y -= 0.012
        return y

    def apply_typed_theme(self):
        try:
            value = parse_color(self.theme_field.text)
        except ValueError as error:
            self.theme_hint.text = str(error)
            self.theme_hint.color = color.hex(settings.WRONG_COLOR)
            return
        self.set_theme(value)

    def set_theme(self, value):
        if self.on_theme:
            self.on_theme(value)

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
                                   position=(5.0, -2.75, 0), scale=1.3)
        self.preview.rotation = (-22, 35, 0)

    def change(self, key, value):
        self.on_change(key, value)
        if key == "stereo":
            self.stereo_note.text = STEREO_NOTE
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
