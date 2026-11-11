import pytest

from logic.theme import (MODES, NAMED_COLORS, PRESETS, THEME_KEYS, build_palette, contrast,
                         parse_color)

SAMPLE_COLORS = ["#ff7a00", "#22d3ee", "#facc15", "#3b0764", "#00ff00", "#0000ff",
                 "#ffffff", "#000000", "#808080", "#ff00ff", "#123456"]


# ---------- разбор цвета ----------
@pytest.mark.parametrize("text, expected", [
    ("#FF7A00", "#ff7a00"), ("ff7a00", "#ff7a00"), ("#f70", "#ff7700"), ("  f70 ", "#ff7700"),
    ("Оранжевый", NAMED_COLORS["оранжевый"]), ("зелёный", NAMED_COLORS["зеленый"]),
    ("ЗЕЛЕНЫЙ", NAMED_COLORS["зеленый"]),
])
def test_parse_color(text, expected):
    assert parse_color(text) == expected


@pytest.mark.parametrize("bad", ["", "   ", "#12345", "#ggg000", "радужный", "12345678"])
def test_parse_color_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_color(bad)


# ---------- палитра ----------
@pytest.mark.parametrize("base", SAMPLE_COLORS + [hex_ for _, hex_ in PRESETS if hex_])
def test_palette_is_complete_and_readable(base):
    p = build_palette(base)
    assert set(THEME_KEYS) <= set(p)
    assert set(p["MODE_COLORS"]) == set(MODES)
    for key in THEME_KEYS:
        assert p[key].startswith("#") and len(p[key]) == 7
    # Текст хорошо читается на фоне и панелях (WCAG AAA для обычного текста - 7)
    assert contrast(p["TEXT_COLOR"], p["SURFACE"]) >= 7
    assert contrast(p["TEXT_STRONG"], p["BACKGROUND"]) >= 7
    # Подписи - хотя бы 3 (крупный и второстепенный текст)
    assert contrast(p["TEXT_MUTED"], p["SURFACE"]) >= 3
    # Белый текст на кнопке главного действия
    assert contrast(p["TEXT_STRONG"], p["SELECTED_COLOR"]) >= 4.5
    # Акцент и цвета режимов заметны на панелях
    assert contrast(p["ACCENT"], p["SURFACE"]) >= 4
    for bright, dim in p["MODE_COLORS"].values():
        assert contrast(bright, p["SURFACE"]) >= 4
        assert contrast(bright, dim) >= 3          # иконка видна на своей подложке


def test_palette_follows_the_chosen_hue():
    """Оранжевая тема - фон тёмно-оранжевый, а не синий."""
    import colorsys
    from logic.theme import hex_to_rgb
    p = build_palette("#ff7a00")
    hue = colorsys.rgb_to_hls(*hex_to_rgb(p["BACKGROUND"]))[0] * 360
    assert 15 <= hue <= 45
    assert p["ACCENT"] != build_palette("#3b82f6")["ACCENT"]


def test_gray_gives_monochrome_theme():
    p = build_palette("серый")
    r, g, b = p["ACCENT"][1:3], p["ACCENT"][3:5], p["ACCENT"][5:7]
    assert r == g == b                               # без цвета


def test_mode_colors_are_distinct():
    for base in SAMPLE_COLORS:
        brights = [bright for bright, _ in build_palette(base)["MODE_COLORS"].values()]
        assert len(set(brights)) == len(MODES)
