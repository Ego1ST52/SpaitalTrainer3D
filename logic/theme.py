"""Пользовательская тема: из ОДНОГО цвета строится вся палитра интерфейса.
Без Ursina - проверяется автотестами.

Как строится палитра (модель HLS: оттенок, светлота, насыщенность):
  * акцент - сам цвет, но достаточно яркий, чтобы читаться на тёмном фоне;
  * фон, панели, рамки, кнопки - тёмные оттенки того же цвета, слегка
    подкрашенные, поэтому интерфейс «в цвет», но не режет глаза;
  * текст - почти белый с лёгким оттенком;
  * пять режимов - соседние оттенки на цветовом круге (гармоничная схема).
Читаемость проверяется по контрастности WCAG (как на сайтах для всех людей).
"""

import colorsys

# Цвета, которые можно написать словами (ё можно не ставить)
NAMED_COLORS = {
    "красный": "#ef4444", "алый": "#ff2400", "малиновый": "#dc143c",
    "вишневый": "#b0103a", "бордовый": "#9b1c31", "рубиновый": "#e0115f",
    "оранжевый": "#f97316", "коралловый": "#ff7f50", "персиковый": "#ffb07c",
    "желтый": "#facc15", "золотой": "#f5c542", "янтарный": "#fbbf24",
    "лаймовый": "#a3e635", "салатовый": "#84cc16", "зеленый": "#22c55e",
    "изумрудный": "#10b981", "мятный": "#2dd4bf", "бирюзовый": "#22d3ee",
    "голубой": "#38bdf8", "синий": "#3b82f6", "индиго": "#6366f1",
    "фиолетовый": "#8b5cf6", "лавандовый": "#a78bfa", "сиреневый": "#c084fc",
    "пурпурный": "#d946ef", "розовый": "#f472b6", "сакура": "#f9a8d4",
    "белый": "#f8fafc", "серый": "#9ca3af", "графитовый": "#6b7280",
    "черный": "#4b5563",
}

# Готовые темы для быстрого выбора: (название, цвет; "" - стандартная)
PRESETS = [
    ("Космос", ""), ("Закат", "#ff7a45"), ("Лес", "#4ade80"), ("Лаванда", "#a78bfa"),
    ("Рубин", "#f43f5e"), ("Океан", "#3b82f6"), ("Мята", "#2dd4bf"), ("Золото", "#facc15"),
    ("Сакура", "#f472b6"), ("Графит", "#9ca3af"),
]

MODES = ["rotation", "matching", "projection", "construction", "custom"]
MODE_HUE_SHIFTS = [0, 40, -40, 80, -80]       # градусы по цветовому кругу

# Какие цвета интерфейса меняет тема (имена как в core/settings.py)
THEME_KEYS = [
    "BACKGROUND", "BACKDROP_GLOW", "BACKDROP_EDGE", "FLOOR_COLOR", "CUBE_CORE",
    "SURFACE", "SURFACE_HOVER", "BUTTON_COLOR", "BUTTON_HOVER", "BORDER", "EDGE_LIGHT",
    "ACCENT", "ACCENT_DIM", "SELECTED_COLOR", "SELECTED_HOVER",
    "TEXT_STRONG", "TEXT_COLOR", "TEXT_MUTED", "NAV_FACE", "NAV_CORE", "HUB_COLOR",
]


# ---------- разбор цвета ----------
def parse_color(text):
    """'#ff7a00', 'ff7a00', '#f70', 'Оранжевый' -> '#ff7a00'.
    Ошибка ValueError с понятным текстом, если цвет не распознан."""
    value = text.strip().lower().replace("ё", "е")
    if not value:
        raise ValueError("Введите цвет, например #ff7a00 или «оранжевый».")
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    digits = value.lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    if len(digits) == 6 and all(ch in "0123456789abcdef" for ch in digits):
        return "#" + digits
    raise ValueError("Не понял цвет. Пример: #ff7a00, #f70 или «мятный».")


def hex_to_rgb(hex_color):
    digits = hex_color.lstrip("#")
    return tuple(int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02x}" for c in rgb)


def hls(h, l, s):
    return rgb_to_hex(colorsys.hls_to_rgb(h % 1.0, l, s))


# ---------- контрастность (WCAG 2.1) ----------
def luminance(hex_color):
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in hex_to_rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """Отношение контрастности от 1 (нет) до 21 (чёрное на белом)."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _readable(h, s, surface, start=0.58, minimum=4.0):
    """Светлота, при которой цвет читается на фоне surface."""
    lightness = start
    while contrast(hls(h, lightness, s), surface) < minimum and lightness < 0.92:
        lightness += 0.02
    return hls(h, lightness, s)


# ---------- палитра ----------
def build_palette(hex_color):
    """Все цвета интерфейса из одного цвета. Возвращает словарь
    {имя из THEME_KEYS: '#rrggbb', 'MODE_COLORS': {режим: (яркий, тёмный)}}."""
    h, _, s = colorsys.rgb_to_hls(*hex_to_rgb(parse_color(hex_color)))
    # Почти бесцветный (серый, белый, чёрный, даже чуть голубоватый серый) -
    # строгая серая тема
    mono = s < 0.15
    accent_s = 0.0 if mono else max(0.55, min(s, 0.9))
    tint = 0.0 if mono else min(s, 0.6) * 0.45     # насколько подкрашен тёмный фон

    p = {
        "BACKGROUND": hls(h, 0.055, tint),
        "BACKDROP_EDGE": hls(h, 0.035, tint),
        "BACKDROP_GLOW": hls(h, 0.17, tint * 1.4),
        "FLOOR_COLOR": hls(h, 0.09, tint),
        "CUBE_CORE": hls(h, 0.14, tint * 0.8),
        "NAV_CORE": hls(h, 0.07, tint),
        "NAV_FACE": hls(h, 0.12, tint * 1.1),
        "SURFACE": hls(h, 0.115, tint),
        "SURFACE_HOVER": hls(h, 0.165, tint * 1.1),
        "BUTTON_COLOR": hls(h, 0.15, tint),
        "BUTTON_HOVER": hls(h, 0.21, tint * 1.1),
        "BORDER": hls(h, 0.22, tint),
        "EDGE_LIGHT": hls(h, 0.3, tint),
        "TEXT_STRONG": hls(h, 0.96, tint * 0.4),
        "TEXT_COLOR": hls(h, 0.85, tint * 0.4),
        "TEXT_MUTED": hls(h, 0.56, tint * 0.5),
        "HUB_COLOR": hls(h, 0.68, tint * 0.6),
    }
    surface = p["SURFACE"]
    p["ACCENT"] = _readable(h, accent_s, surface)
    p["ACCENT_DIM"] = hls(h, 0.17, accent_s * 0.6)
    # Кнопка «главного действия»: темнеет, пока белый текст на ней не станет
    # читаемым (у жёлтого и зелёного при той же светлоте контраст хуже)
    lightness = 0.36
    while contrast(p["TEXT_STRONG"], hls(h, lightness, accent_s * 0.85)) < 4.8             and lightness > 0.12:
        lightness -= 0.02
    p["SELECTED_COLOR"] = hls(h, lightness, accent_s * 0.85)
    p["SELECTED_HOVER"] = hls(h, lightness + 0.06, accent_s * 0.85)

    modes = {}
    for i, (mode, shift) in enumerate(zip(MODES, MODE_HUE_SHIFTS)):
        if mono:
            bright = hls(h, 0.85 - i * 0.06, 0)
        else:
            bright = _readable(h + shift / 360, accent_s, surface)
        modes[mode] = (bright, hls(h + shift / 360, 0.17, accent_s * 0.6))
    p["MODE_COLORS"] = modes
    return p
