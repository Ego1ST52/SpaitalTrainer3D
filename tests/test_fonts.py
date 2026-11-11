"""Русские буквы в полях ввода (имя игрока, код тренировки)."""

from pathlib import Path

import pytest

import ursina
from core.fonts import CANDIDATES, find_monospace_cyrillic, has_cyrillic

URSINA_FONTS = Path(ursina.__file__).parent / "fonts"


def test_builtin_monospace_font_has_no_cyrillic():
    """Причина бага: встроенный моноширинный шрифт Ursina без русских букв."""
    assert not has_cyrillic(URSINA_FONTS / "VeraMono.ttf")
    assert has_cyrillic(URSINA_FONTS / "OpenSans-Regular.ttf")


def test_missing_font_file_is_not_cyrillic(tmp_path):
    assert not has_cyrillic(tmp_path / "nope.ttf")


def test_find_skips_folders_without_suitable_fonts(tmp_path):
    assert find_monospace_cyrillic(tmp_path) is None


def test_system_monospace_font_found():
    found = find_monospace_cyrillic()
    if found is None:
        pytest.skip("в системе нет Consolas / Lucida Console / Courier New")
    assert found.name in CANDIDATES and has_cyrillic(found)


def test_cyrillic_name_typed_into_profiles_field(ursina_app):
    """Набираем «Аня» в поле имени: текст в поле и шрифт поля умеют кириллицу."""
    from ursina import Text
    from core.fonts import cache_folder
    from core.scene_manager import SceneManager
    from interface.profiles_screen import ProfilesScreen

    created = []
    screen = ProfilesScreen(SceneManager(), [], None, lambda uid: None,
                            lambda name: created.append(name))
    screen.navigate = lambda *args, **kwargs: None
    try:
        field = screen.name_field.text_field
        assert field.active                            # печатать можно без клика
        for ch in "Аня":
            field.text_input(ch)
        screen.create()
        assert created == ["Аня"]
        if find_monospace_cyrillic() is not None:
            assert has_cyrillic(cache_folder() / Text.default_monospace_font)
    finally:
        screen.close()
