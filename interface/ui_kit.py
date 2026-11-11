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

TONES = {
    "text": settings.TEXT_COLOR,
    "strong": settings.TEXT_STRONG,
    "muted": settings.TEXT_MUTED,
    "accent": settings.ACCENT,
    "correct": settings.CORRECT_COLOR,
    "wrong": settings.WRONG_COLOR,
}

# Текст и иконки рисуем чуть ближе к камере, чем фон, чтобы они не мерцали
FRONT = -0.01


def rounded_quad(width, height, radius):
    """Прямоугольник со скруглёнными углами. radius - в экранных единицах."""
    return Quad(radius=min(radius / height, 0.5), aspect=width / height)


def label(text, position, size=1.0, tone="text", origin=(-0.5, 0), parent=None):
    """Надпись. tone - один из ключей TONES. origin (-0.5, 0) - выравнивание
    по левому краю, (0, 0) - по центру."""
    x, y = position
    return Text(text, parent=parent or camera.ui, position=(x, y, FRONT),
                scale=size, origin=origin, color=color.hex(TONES[tone]))


class Panel(Entity):
    """Скруглённая подложка с тонкой рамкой."""

    def __init__(self, width, height, position=(0, 0), fill=settings.SURFACE,
                 border=settings.BORDER, radius=0.018, parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        if border:
            edge = 0.003
            Entity(parent=self, model=rounded_quad(width + 2 * edge, height + 2 * edge,
                                                   radius + edge),
                   scale=(width + 2 * edge, height + 2 * edge),
                   color=color.hex(border), shader=unlit_shader, z=0.002)
        Entity(parent=self, model=rounded_quad(width, height, radius),
               scale=(width, height), color=color.hex(fill),
               shader=unlit_shader, z=0.001)


class UIButton(Button):
    """Кнопка. variant: 'primary' (главное действие на экране, одно),
    'secondary' (обычная) или 'ghost' (тихая, почти без фона)."""

    VARIANTS = {
        # фон, фон под курсором, цвет текста
        "primary": (settings.SELECTED_COLOR, "#1590ab", settings.TEXT_STRONG),
        "secondary": (settings.BUTTON_COLOR, settings.BUTTON_HOVER, settings.TEXT_COLOR),
        "ghost": (settings.SURFACE, settings.SURFACE_HOVER, settings.TEXT_MUTED),
        # подсветка ответа после выбора
        "correct": ("#14532d", "#166534", "#bbf7d0"),
        "wrong": ("#7f1d1d", "#991b1b", "#fecaca"),
    }

    def __init__(self, text, on_click, position=(0, 0), scale=(0.3, 0.065),
                 variant="secondary", parent=None, text_size=0.9, swatch=None):
        super().__init__(text=text, parent=parent or camera.ui, position=position,
                         scale=scale, radius=0.3, text_size=text_size)
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
        fill, hover, text_color = self.VARIANTS[variant]
        self.variant = variant
        self.color = color.hex(fill)
        self.highlight_color = color.hex(hover)
        self.pressed_color = color.hex(hover).tint(-0.1)
        self.text_color = color.hex(text_color)
        self.highlight_text_color = color.hex(text_color)
        # Если курсор уже над кнопкой, сразу показываем цвет наведения
        self.model.setColorScale(self.highlight_color if self.hovered else self.color)


def _draw_icon(kind, parent):
    """Простые иконки из фигур (в шрифте нет нужных символов)."""
    accent = color.hex(settings.ACCENT)
    if kind == "rotation":
        label("90°", (0, 0), 1.05, "accent", origin=(0, 0), parent=parent)
    elif kind == "matching":
        # Две одинаковые фигуры, одна повёрнута
        Entity(parent=parent, model="quad", scale=0.022, position=(-0.013, 0, FRONT),
               color=accent, shader=unlit_shader)
        Entity(parent=parent, model="quad", scale=0.022, position=(0.014, 0, FRONT),
               rotation_z=45, color=accent, shader=unlit_shader)


class ModeCard(Entity):
    """Карточка режима: иконка, название, описание. При наведении
    подсвечивается рамка и карточка немного сдвигается вправо."""

    def __init__(self, title, subtitle, icon, on_click, position,
                 width=0.62, height=0.115, parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        self.home_x = position[0]
        radius = 0.02
        edge = 0.003

        self.border = Entity(parent=self, model=rounded_quad(width + 2 * edge,
                                                             height + 2 * edge,
                                                             radius + edge),
                             scale=(width + 2 * edge, height + 2 * edge),
                             color=color.hex(settings.BORDER),
                             shader=unlit_shader, z=0.002)
        self.button = Button(parent=self, scale=(width, height), radius=radius / height,
                             color=color.hex(settings.SURFACE),
                             highlight_color=color.hex(settings.SURFACE_HOVER),
                             pressed_color=color.hex(settings.SURFACE_HOVER),
                             z=0.001)
        self.button.on_click = on_click

        icon_x = -width / 2 + 0.018 + 0.038
        Panel(0.076, 0.076, position=(icon_x, 0, FRONT / 2), fill=settings.ACCENT_DIM,
              border=None, radius=0.016, parent=self)
        icon_holder = Entity(parent=self, position=(icon_x, 0))
        _draw_icon(icon, icon_holder)

        text_x = icon_x + 0.06
        label(title, (text_x, 0.017), 1.15, "strong", parent=self)
        label(subtitle, (text_x, -0.022), 0.85, "muted", parent=self)
        label("›", (width / 2 - 0.035, 0.004), 2.2, "accent", origin=(0, 0), parent=self)

    def update(self):
        hovered = self.button.hovered
        target = self.home_x + (0.012 if hovered else 0)
        self.x = lerp(self.x, target, min(1, time.dt * 12))
        self.border.color = color.hex(settings.ACCENT if hovered else settings.BORDER)


class Segmented(Entity):
    """Переключатель из нескольких сегментов (выбран ровно один).
    options: [(ключ, подпись), ...]; on_change(ключ) вызывается при выборе."""

    def __init__(self, options, selected, on_change, position,
                 width=0.62, height=0.062, parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        self.on_change = on_change
        self.buttons = {}
        Panel(width, height, fill=settings.SURFACE, radius=height * 0.3, parent=self)

        pad = 0.006
        count = len(options)
        segment = (width - pad * (count + 1)) / count
        for i, (key, text) in enumerate(options):
            x = -width / 2 + pad + i * (segment + pad) + segment / 2
            self.buttons[key] = UIButton(text, lambda k=key: self.select(k),
                                         position=(x, 0, FRONT / 2),
                                         scale=(segment, height - 2 * pad),
                                         variant="ghost", parent=self, text_size=0.85)
        self.select(selected, notify=False)

    def select(self, key, notify=True):
        self.selected = key
        for k, button in self.buttons.items():
            button.set_variant("primary" if k == key else "ghost")
        if notify:
            self.on_change(key)


class TopBar(Entity):
    """Верхняя панель игрового экрана: режим и уровень слева, полоска
    прогресса по центру, баллы и кнопка «В меню» справа."""

    def __init__(self, title, on_back, length, parent=None):
        super().__init__(parent=parent or camera.ui)
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.length = length

        label(title, (left, 0.445), 1.3, "strong", parent=self)
        self.level_text = label("", (left, 0.405), 0.8, "muted", parent=self)

        self.progress_text = label("", (0, 0.452), 0.8, "muted", origin=(0, 0),
                                   parent=self)
        self.segments_holder = Entity(parent=self, position=(0, 0.418))

        label("Баллы", (right - 0.32, 0.452), 0.8, "muted", parent=self)
        self.points_text = label("0", (right - 0.32, 0.415), 1.3, "accent", parent=self)
        UIButton("В меню", on_back, position=(right - 0.09, 0.43),
                 scale=(0.18, 0.055), variant="ghost", parent=self)

    def update_state(self, level, results, answered, points):
        """results - список TaskResult. answered - ответ на текущее уже дан."""
        self.level_text.text = (f"{settings.LEVEL_NAMES[level]} уровень  •  "
                                "сменить: клавиши 1, 2, 3")
        number = len(results) if answered else len(results) + 1
        self.progress_text.text = f"Задание {min(number, self.length)} из {self.length}"
        self.points_text.text = str(points)

        for child in list(self.segments_holder.children):
            destroy(child)
        width, gap = 0.5, 0.006
        segment = (width - gap * (self.length - 1)) / self.length
        for i in range(self.length):
            if i < len(results):
                hex_color = settings.CORRECT_COLOR if results[i].correct else settings.WRONG_COLOR
            elif i == len(results):
                hex_color = settings.ACCENT       # текущее задание
            else:
                hex_color = settings.BORDER       # ещё впереди
            Entity(parent=self.segments_holder, model="quad", shader=unlit_shader,
                   position=(-width / 2 + segment / 2 + i * (segment + gap), 0, FRONT),
                   scale=(segment, 0.008), color=color.hex(hex_color))


class StatTile(Entity):
    """Плитка с показателем: подпись сверху, крупное значение снизу."""

    def __init__(self, caption, value, position, width=0.26, height=0.1,
                 tone="strong", parent=None):
        super().__init__(parent=parent or camera.ui, position=position)
        Panel(width, height, fill=settings.SURFACE, border=None, radius=0.016, parent=self)
        left = -width / 2 + 0.02
        label(caption, (left, 0.022), 0.8, "muted", parent=self)
        self.value = label(value, (left, -0.016), 1.35, tone, parent=self)
