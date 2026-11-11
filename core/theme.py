"""Применение пользовательской темы ко всему интерфейсу.

Все экраны берут цвета из core/settings.py в момент создания. Поэтому
сменить тему = переписать цвета в settings; следующий открытый экран
уже будет в новых цветах (а текущий экран просто открываем заново).
Стандартные цвета запоминаются при запуске, чтобы к ним можно было вернуться.
"""

import copy

from core import settings
from logic.theme import THEME_KEYS, build_palette

_DEFAULTS = {key: getattr(settings, key) for key in THEME_KEYS}
_DEFAULT_MODES = copy.deepcopy(settings.MODE_COLORS)


def default_palette():
    return {**_DEFAULTS, "MODE_COLORS": copy.deepcopy(_DEFAULT_MODES)}


def apply_theme(color=""):
    """color - '#rrggbb' пользовательской темы или "" для стандартной."""
    palette = build_palette(color) if color else default_palette()
    for key in THEME_KEYS:
        setattr(settings, key, palette[key])
    # Словарь меняем на месте: другие модули держат ссылку именно на него
    settings.MODE_COLORS.clear()
    settings.MODE_COLORS.update(copy.deepcopy(palette["MODE_COLORS"]))
    return palette
