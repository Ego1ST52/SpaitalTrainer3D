"""Общие элементы интерфейса в едином стиле.

Все экраны собираются из этих деталей, поэтому стиль (цвета, скругления,
реакция на наведение) задаётся в одном месте. Каждый элемент - это Entity,
внутри которого лежат его части. Значит, удаляя элемент (dispose), мы
удаляем и всё, что внутри, - ничего не «зависает» на экране.

Координаты - экранные (camera.ui): по вертикали от -0.5 до 0.5,
по горизонтали примерно от -0.89 до 0.89 на мониторе 16:9.
"""

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from core import sounds
from core.preferences import prefs
from logic.tutorials import TUTORIALS

# Тона текста. Цвета читаются из settings в момент создания надписи, а не
# при запуске программы, - так работает смена темы (см. core/theme.py).
TONES = {
    "text": "TEXT_COLOR",
    "strong": "TEXT_STRONG",
    "muted": "TEXT_MUTED",
    "accent": "ACCENT",
    "correct": "CORRECT_COLOR",
    "wrong": "WRONG_COLOR",
}
_DEFAULT = object()      # «значение по умолчанию из текущей темы»


def tone_color(tone):
    """Ключ из TONES или цвет '#rrggbb' -> '#rrggbb'."""
    return getattr(settings, TONES[tone]) if tone in TONES else tone

# Текст и иконки рисуем чуть ближе к камере, чем фон, чтобы они не мерцали
FRONT = -0.01


def mode_color(mode):
    """Яркий цвет режима (у каждого режима свой)."""
    return settings.MODE_COLORS[mode][0]


def mode_dim(mode):
    """Тёмная подложка в цвете режима."""
    return settings.MODE_COLORS[mode][1]


def with_alpha(hex_color, alpha):
    c = color.hex(hex_color)
    return color.rgba(c.r, c.g, c.b, alpha)


def rounded_quad(width, height, radius, outline=False):
    """Прямоугольник со скруглёнными углами (radius - в экранных единицах).
    outline=True - только контур (рамка), без заливки."""
    if outline:
        return Quad(radius=min(radius / height, 0.5), aspect=width / height,
                    mode="line", thickness=1.5)
    return Quad(radius=min(radius / height, 0.5), aspect=width / height)


def label(text, position, size=1.0, tone="text", origin=(-0.5, 0), parent=None):
    """Надпись. tone - ключ из TONES или цвет '#rrggbb'. origin (-0.5, 0) -
    выравнивание по левому краю, (0, 0) - по центру, (0.5, 0) - по правому."""
    x, y = position
    hex_color = tone_color(tone)
    return Text(text, parent=parent or camera.ui, position=(x, y, FRONT),
                scale=size, origin=origin, color=color.hex(hex_color))


class Panel(Entity):
    """Полупрозрачная («стеклянная») подложка с тонкой рамкой
    и светлой кромкой сверху."""

    def __init__(self, width, height, position=(0, 0), fill=None, border=_DEFAULT,
                 radius=0.018, alpha=None, parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        fill = fill or settings.SURFACE
        border = settings.BORDER if border is _DEFAULT else border
        alpha = settings.SURFACE_ALPHA if alpha is None else alpha
        Entity(parent=self, model=rounded_quad(width, height, radius),
               scale=(width, height), color=with_alpha(fill, alpha),
               shader=unlit_shader, z=0.002)
        if border:
            Entity(parent=self, model=rounded_quad(width, height, radius, outline=True),
                   scale=(width, height), color=color.hex(border),
                   shader=unlit_shader, z=0.001)
            Entity(parent=self, model="quad", shader=unlit_shader,
                   position=(0, height / 2 - 0.0015, 0.0005),
                   scale=(width - 2 * radius, 0.0015), color=color.hex(settings.EDGE_LIGHT))


class UIButton(Button):
    """Кнопка. variant: 'primary' (главное действие на экране, одно),
    'secondary' (обычная) или 'ghost' (тихая, почти без фона)."""

    @staticmethod
    def variants():
        """Цвета вариантов кнопки из текущей темы: фон, фон под курсором, текст."""
        return {
            "primary": (settings.SELECTED_COLOR, settings.SELECTED_HOVER, settings.TEXT_STRONG),
            "secondary": (settings.BUTTON_COLOR, settings.BUTTON_HOVER, settings.TEXT_COLOR),
            "ghost": (settings.SURFACE, settings.SURFACE_HOVER, settings.TEXT_MUTED),
            # подсветка ответа после выбора - не зависит от темы
            "correct": ("#14532d", "#166534", "#bbf7d0"),
            "wrong": ("#7f1d1d", "#991b1b", "#fecaca"),
        }

    def __init__(self, text, on_click, position=(0, 0), scale=(0.3, 0.065),
                 variant="secondary", parent=None, text_size=0.9, swatch=None, radius=0.3):
        super().__init__(text=text, parent=parent or camera.ui, position=position,
                         scale=scale, radius=radius, text_size=text_size)
        self.on_click = on_click
        self.set_variant(variant)
        if swatch:
            # Цветной квадратик у левого края. Кнопка растянута до scale,
            # поэтому размеры делим на scale, чтобы квадрат остался квадратом.
            width, height = scale
            size = 0.024
            Entity(parent=self, model=rounded_quad(size, size, 0.005),
                   position=(-0.5 + 0.03 / width, 0, -0.02),
                   scale=(size / width, size / height),
                   color=color.hex(swatch), shader=unlit_shader)

    def set_variant(self, variant):
        fill, hover, text_color = self.variants()[variant]
        self.variant = variant
        self.color = color.hex(fill)
        self.highlight_color = color.hex(hover)
        self.pressed_color = color.hex(hover).tint(-0.1)
        self.text_color = color.hex(text_color)
        self.highlight_text_color = color.hex(text_color)
        # Если курсор уже над кнопкой, сразу показываем цвет наведения
        self.model.setColorScale(self.highlight_color if self.hovered else self.color)


class LogoMark(Entity):
    """Фирменный знак: изометрический кубик из трёх граней."""

    def __init__(self, position, size=0.045, parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        r = size / 2
        w = r * 0.866           # cos(30°)
        top, center, bottom = Vec3(0, r, 0), Vec3(0, 0, 0), Vec3(0, -r, 0)
        up_left, up_right = Vec3(-w, r / 2, 0), Vec3(w, r / 2, 0)
        low_left, low_right = Vec3(-w, -r / 2, 0), Vec3(w, -r / 2, 0)
        faces = [
            ((top, up_right, center, up_left), settings.TEXT_STRONG),        # верх
            ((up_left, center, bottom, low_left), settings.ACCENT),          # левая
            ((center, up_right, low_right, bottom), settings.SELECTED_COLOR),  # правая
        ]
        for corners, hex_color in faces:
            Entity(parent=self, shader=unlit_shader, double_sided=True,
                   model=Mesh(vertices=list(corners), triangles=[(0, 1, 2), (0, 2, 3)]),
                   color=color.hex(hex_color), z=FRONT)


def _draw_icon(kind, parent, hex_color):
    """Простые иконки из фигур (в шрифте нет нужных символов)."""
    tint = color.hex(hex_color)
    if kind == "rotation":
        label("90°", (0, 0), 1.05, hex_color, origin=(0, 0), parent=parent)
    elif kind == "matching":
        # Две одинаковые фигуры, одна повёрнута
        Entity(parent=parent, model="quad", scale=0.022, position=(-0.013, 0, FRONT),
               color=tint, shader=unlit_shader)
        Entity(parent=parent, model="quad", scale=0.022, position=(0.014, 0, FRONT),
               rotation_z=45, color=tint, shader=unlit_shader)
    elif kind == "custom":
        # Четыре клетки в цветах всех режимов - «смесь»
        for (cx, cy), mode in zip(((-0.011, 0.011), (0.011, 0.011), (-0.011, -0.011),
                                   (0.011, -0.011)),
                                  ("rotation", "matching", "projection", "construction")):
            Entity(parent=parent, model="quad", scale=0.019, position=(cx, cy, FRONT),
                   color=color.hex(mode_color(mode)), shader=unlit_shader)
    elif kind == "construction":
        # Лесенка из кубиков: 1 + 2 + 3
        for cx, cy in ((-0.016, -0.016), (0, -0.016), (0.016, -0.016),
                       (0, 0), (0.016, 0), (0.016, 0.016)):
            Entity(parent=parent, model="quad", scale=0.0145, position=(cx, cy, FRONT),
                   color=tint, shader=unlit_shader)
    elif kind == "projection":
        # Плоская «тень» фигуры: три клетки уголком
        for cx, cy in ((-0.011, -0.011), (0.011, -0.011), (-0.011, 0.011)):
            Entity(parent=parent, model="quad", scale=0.019, position=(cx, cy, FRONT),
                   color=tint, shader=unlit_shader)


class ModeCard(Entity):
    """Карточка режима: номер, иконка, название, описание. При наведении
    рамка и полоска слева загораются цветом режима, карточка сдвигается.
    appear_delay - карточки выезжают по очереди при открытии меню."""

    def __init__(self, number, title, subtitle, mode, on_click, position,
                 width=0.62, height=0.105, appear_delay=0.0, parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        self.home_x = position[0]
        if not prefs.reduce_motion:
            self.x = self.home_x - 0.06          # старт чуть левее - «выезд»
        self.appear_at = time.time() + appear_delay
        self.accent = color.hex(mode_color(mode))
        radius = 0.02

        self.button = Button(parent=self, scale=(width, height), radius=radius / height,
                             color=with_alpha(settings.SURFACE, settings.SURFACE_ALPHA),
                             highlight_color=color.hex(settings.SURFACE_HOVER),
                             pressed_color=color.hex(settings.SURFACE_HOVER), z=0.002)
        self.button.on_click = on_click
        self.border = Entity(parent=self, model=rounded_quad(width, height, radius, True),
                             scale=(width, height), color=color.hex(settings.BORDER),
                             shader=unlit_shader, z=0.001)
        self.bar = Entity(parent=self, model=rounded_quad(0.006, height * 0.55, 0.003),
                          scale=(0.006, height * 0.55), position=(-width / 2 + 0.01, 0, FRONT),
                          color=self.accent, shader=unlit_shader, enabled=False)

        label(number, (-width / 2 + 0.03, 0), 0.8, "muted", parent=self)
        icon_x = -width / 2 + 0.11
        Panel(0.07, 0.07, position=(icon_x, 0, FRONT / 2), fill=mode_dim(mode),
              border=None, radius=0.016, alpha=1, parent=self)
        icon_holder = Entity(parent=self, position=(icon_x, 0))
        _draw_icon(mode, icon_holder, mode_color(mode))

        text_x = icon_x + 0.055
        label(title, (text_x, 0.016), 1.1, "strong", parent=self)
        label(subtitle, (text_x, -0.02), 0.8, "muted", parent=self)
        self.chevron = label("›", (width / 2 - 0.035, 0.004), 2.0, "muted",
                             origin=(0, 0), parent=self)

    def update(self):
        if time.time() < self.appear_at:
            return
        hovered = self.button.hovered
        target = self.home_x + (0.012 if hovered else 0)
        self.x = lerp(self.x, target, min(1, time.dt * 10))
        self.border.color = self.accent if hovered else color.hex(settings.BORDER)
        self.chevron.color = self.accent if hovered else color.hex(settings.TEXT_MUTED)
        self.bar.enabled = hovered


class Segmented(Entity):
    """Переключатель из нескольких сегментов (выбран ровно один).
    options: [(ключ, подпись), ...]; on_change(ключ) вызывается при выборе."""

    def __init__(self, options, selected, on_change, position,
                 width=0.62, height=0.062, parent=None, text_size=0.85):
        super().__init__(parent=parent or camera.ui, position=position)
        self.on_change = on_change
        self.buttons = {}
        Panel(width, height, radius=height * 0.3, parent=self)

        pad = 0.006
        count = len(options)
        segment = (width - pad * (count + 1)) / count
        for i, (key, text) in enumerate(options):
            x = -width / 2 + pad + i * (segment + pad) + segment / 2
            self.buttons[key] = UIButton(text, lambda k=key: self.select(k),
                                         position=(x, 0, FRONT / 2),
                                         scale=(segment, height - 2 * pad),
                                         variant="ghost", parent=self, text_size=text_size)
        self.select(selected, notify=False)

    def select(self, key, notify=True):
        self.selected = key
        for k, button in self.buttons.items():
            button.set_variant("primary" if k == key else "ghost")
        if notify:
            self.on_change(key)

    def clear(self):
        """Снять выделение (когда выбор сделан в другом, связанном ряду)."""
        self.selected = object()
        for button in self.buttons.values():
            button.set_variant("ghost")


class TopBar(Entity):
    """Верхняя панель игрового экрана: режим и уровень слева, полоска
    прогресса по центру, баллы и кнопка «В меню» справа."""

    def __init__(self, mode, on_back, parent=None):
        super().__init__(parent=parent or camera.ui)
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.accent = mode_color(mode)

        Entity(parent=self, model=rounded_quad(0.006, 0.05, 0.003), scale=(0.006, 0.05),
               position=(left, 0.43, FRONT), color=color.hex(self.accent),
               shader=unlit_shader)
        label(settings.MODE_NAMES[mode], (left + 0.02, 0.445), 1.3, "strong", parent=self)
        self.level_text = label("", (left + 0.02, 0.408), 0.8, "muted", parent=self)

        self.progress_text = label("", (0, 0.452), 0.8, "muted", origin=(0, 0),
                                   parent=self)
        self.segments_holder = Entity(parent=self, position=(0, 0.418))
        # Короткое сообщение под полоской прогресса («Уровень повышен: ...»)
        self.flash_text = label("", (0, 0.38), 0.85, self.accent, origin=(0, 0), parent=self)
        self.flash_left = 0.0

        label("Баллы", (right - 0.36, 0.452), 0.8, "muted", parent=self)
        self.points_text = label("0", (right - 0.36, 0.415), 1.3, self.accent, parent=self)
        UIButton("В меню", on_back, position=(right - 0.09, 0.43),
                 scale=(0.18, 0.055), variant="ghost", parent=self)

        # Подсказка «Как играть»: кнопка «?» и автоматически при первом входе
        self.mode = mode
        self.dialog = None
        if mode in TUTORIALS:
            UIButton("?", self.show_help, position=(right - 0.215, 0.43), scale=(0.05, 0.055),
                     variant="ghost", parent=self, text_size=1.1)
            seen = prefs.get("seen_tutorials")
            if mode not in seen:
                prefs.save("seen_tutorials", seen + [mode])
                self.show_help()

    def show_help(self):
        if self.dialog is None:
            self.dialog = TutorialDialog(self.mode, self.close_help, parent=self)

    def close_help(self):
        if self.dialog is not None:
            destroy_tree(self.dialog)
            self.dialog = None

    def update_state(self, session, answered):
        """session - текущая тренировка, answered - ответ на задание уже дан."""
        note = getattr(session, "note", "")
        level_name = settings.LEVEL_NAMES[session.current_level]
        self.level_text.text = f"{level_name} уровень  •  {note}" if note else             f"{level_name} уровень"
        results, length, points = session.results, session.length, session.points
        playlist = getattr(session, "playlist", None)
        if playlist is not None:
            # «Моя тренировка»: прогресс и баллы за всю тренировку, а не за этап
            results = playlist.all_results + session.results
            length, points = playlist.total_tasks, playlist.points + session.points
        number = len(results) if answered else len(results) + 1
        self.progress_text.text = f"Задание {min(number, length)} из {length}"
        self.points_text.text = str(points)

        for child in list(self.segments_holder.children):
            destroy(child)
        width = 0.5
        gap = 0.006 if length <= 10 else 0.003
        segment = (width - gap * (length - 1)) / length
        for i in range(length):
            if i < len(results):
                hex_color = settings.CORRECT_COLOR if results[i].correct else settings.WRONG_COLOR
            elif i == len(results):
                hex_color = self.accent           # текущее задание
            else:
                hex_color = settings.BORDER       # ещё впереди
            Entity(parent=self.segments_holder, model="quad", shader=unlit_shader,
                   position=(-width / 2 + segment / 2 + i * (segment + gap), 0, FRONT),
                   scale=(segment, 0.008), color=color.hex(hex_color))


    def flash_level(self, session):
        """Вызывается после каждого ответа: звук «верно/неверно», а если
        сменился уровень (адаптивная сложность) - надпись под полоской."""
        if session.results:
            sounds.play("correct" if session.results[-1].correct else "wrong")
        change = session.level_change
        if change is None:
            return
        if change == "up":
            sounds.play("level_up")
        word = "повышен" if change == "up" else "понижен"
        self.flash_text.text = f"Уровень {word}: {settings.LEVEL_NAMES[session.current_level]}"
        self.flash_text.color = color.hex(settings.CORRECT_COLOR if change == "up"
                                          else settings.TEXT_COLOR)
        self.flash_left = 2.5

    def update(self):
        if self.flash_left > 0:
            self.flash_left -= time.dt
            if self.flash_left <= 0:
                self.flash_text.text = ""


def destroy_tree(entity):
    """Удалить объект со всем содержимым (как engine.objects.dispose)."""
    for child in list(entity.children):
        destroy_tree(child)
    destroy(entity)


class Avatar(Entity):
    """Кружок цвета игрока с первой буквой имени."""

    def __init__(self, name, hex_color, position, size=0.05, parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        # model="circle", а не Circle(...): Circle() в Ursina при каждом вызове
        # оставляет за собой лишний служебный объект (найдено тестом утечек)
        Entity(parent=self, model="circle", scale=size, color=color.hex(hex_color),
               shader=unlit_shader, z=FRONT / 2)
        label(name[:1].upper(), (0, 0.001), size * 22, "#0b1220", origin=(0, 0), parent=self)


class PlayerChip(Entity):
    """Плашка текущего игрока (аватар, имя). Клик - сменить игрока."""

    def __init__(self, name, hex_color, on_click, position, width=0.3, height=0.07,
                 parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        UIButton("", on_click, scale=(width, height), variant="ghost", parent=self,
                 radius=0.4)
        left = -width / 2 + 0.04
        Avatar(name, hex_color, (left, 0, FRONT), size=0.045, parent=self)
        label(name, (left + 0.04, 0.012), 0.9, "strong", parent=self)
        label("сменить игрока  ›", (left + 0.04, -0.016), 0.7, "muted", parent=self)


class StatTile(Entity):
    """Плитка с показателем: подпись сверху, крупное значение снизу."""

    def __init__(self, caption, value, position, width=0.26, height=0.1,
                 tone="strong", parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        Panel(width, height, radius=0.016, parent=self)
        left = -width / 2 + 0.02
        label(caption, (left, 0.022), 0.8, "muted", parent=self)
        self.value = label(value, (left, -0.016), 1.35, tone, parent=self)


# Импорт в конце файла: окно подсказки само использует детали из этого модуля
from interface.tutorial_dialog import TutorialDialog  # noqa: E402
