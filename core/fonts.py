"""Шрифт для полей ввода (имя игрока, код тренировки).

Поле ввода Ursina рисует текст МОНОШИРИННЫМ шрифтом (у всех букв одна
ширина - так поле ставит курсор). Встроенный в Ursina VeraMono.ttf не
содержит русских букв: они вводятся, но вместо них видны пустые квадраты.

В Windows есть моноширинные шрифты с кириллицей. Копировать их в проект
нельзя (лицензия Microsoft), поэтому при запуске берём шрифт из системы
и кладём копию в служебную папку программы на этом же компьютере.
"""

import os
import shutil
import tempfile
from pathlib import Path

from PIL import ImageFont

# По порядку: Consolas, Lucida Console, Courier New
CANDIDATES = ("consola.ttf", "lucon.ttf", "cour.ttf")
CYRILLIC_SAMPLE = "АБВЖЯабвжяЁё"


def has_cyrillic(font_path):
    """Есть ли в шрифте русские буквы (не «пустые квадраты»)."""
    try:
        font = ImageFont.truetype(str(font_path), 32)
    except OSError:
        return False
    missing = font.getmask("\uffff").getbbox()     # так выглядит отсутствующий символ
    return all(font.getmask(ch).getbbox() not in (None, missing) for ch in CYRILLIC_SAMPLE)


def windows_fonts_folder():
    return Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def find_monospace_cyrillic(folder=None):
    """Путь к первому подходящему шрифту или None."""
    folder = Path(folder) if folder else windows_fonts_folder()
    for name in CANDIDATES:
        path = folder / name
        if path.exists() and has_cyrillic(path):
            return path
    return None


def cache_folder():
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(base) / "SpatialTrainer3D" / "fonts"


def setup_input_font(system_folder=None):
    """Настроить Ursina так, чтобы поля ввода показывали русские буквы.
    Возвращает имя выбранного шрифта или None (тогда остаётся прежний)."""
    from ursina import Text, application

    source = find_monospace_cyrillic(system_folder)
    if source is None:
        return None
    try:
        folder = cache_folder()
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / source.name
        if not target.exists():
            shutil.copy2(source, target)
    except OSError as error:
        print("Не удалось подготовить шрифт для полей ввода:", error)
        return None
    # Ursina ищет шрифты сначала в application.fonts_folder - даём ей нашу
    # маленькую папку (искать по всей системной папке было бы медленно)
    application.fonts_folder = folder
    Text.default_monospace_font = source.name
    return source.name
