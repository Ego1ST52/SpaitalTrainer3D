"""Скины куба для режима «Вращение»: как выглядят и как называются грани.
Без Ursina - проверяется автотестами.

Грани обозначены как в logic/rotations.py: '+X' (справа), '-X' (слева),
'+Y' (верх), '-Y' (низ), '+Z' (сзади), '-Z' (спереди, к зрителю).
Для каждого скина грань имеет название (оно же - вариант ответа) и цвет.
"""

SKINS = {
    "classic": {
        "title": "Цвета",
        "faces": {
            "+X": ("красный", "#e63946"), "-X": ("оранжевый", "#f77f00"),
            "+Y": ("белый", "#f1f5f9"), "-Y": ("жёлтый", "#ffd166"),
            "+Z": ("синий", "#2a6fdb"), "-Z": ("зелёный", "#2a9d5c"),
        },
    },
    # Палитра Окабе - Ито: цвета различимы при самых частых видах дальтонизма.
    # Названия те же, а на гранях всегда есть буквы - можно не полагаться на цвет.
    "colorblind": {
        "title": "Для дальтоников",
        "faces": {
            "+X": ("красный", "#d55e00"), "-X": ("оранжевый", "#e69f00"),
            "+Y": ("белый", "#f1f5f9"), "-Y": ("жёлтый", "#f0e442"),
            "+Z": ("синий", "#0072b2"), "-Z": ("зелёный", "#009e73"),
        },
        "always_marks": True,
    },
    # Скины-награды: открываются достижениями (см. logic/achievements.py)
    "neon": {
        "title": "Неон",
        "faces": {
            "+X": ("красный", "#ff2d55"), "-X": ("оранжевый", "#ff9f0a"),
            "+Y": ("белый", "#f5f5f7"), "-Y": ("жёлтый", "#ffd60a"),
            "+Z": ("синий", "#0a84ff"), "-Z": ("зелёный", "#30d158"),
        },
    },
    "pastel": {
        "title": "Пастель",
        "faces": {
            "+X": ("красный", "#f19a9a"), "-X": ("оранжевый", "#f6bf8c"),
            "+Y": ("белый", "#fbfbfb"), "-Y": ("жёлтый", "#f7e08f"),
            "+Z": ("синий", "#93b7ee"), "-Z": ("зелёный", "#98d6aa"),
        },
    },
    "jewel": {
        "title": "Самоцветы",
        "faces": {
            "+X": ("красный", "#b3243c"), "-X": ("оранжевый", "#d2731a"),
            "+Y": ("белый", "#ece9e4"), "-Y": ("жёлтый", "#dcaa1e"),
            "+Z": ("синий", "#2347b8"), "-Z": ("зелёный", "#13895a"),
        },
    },
    # Игральная кость: сумма точек на противоположных гранях равна 7
    "dice": {
        "title": "Игральная кость",
        "faces": {
            "+Y": ("1", "#f1f5f9"), "-Y": ("6", "#f1f5f9"),
            "-Z": ("2", "#f1f5f9"), "+Z": ("5", "#f1f5f9"),
            "+X": ("3", "#f1f5f9"), "-X": ("4", "#f1f5f9"),
        },
        "pips": True,
    },
}

# Где рисовать точки на грани кости (координаты в долях грани от -0.5 до 0.5)
_A = 0.27
PIP_LAYOUT = {
    1: [(0, 0)],
    2: [(-_A, -_A), (_A, _A)],
    3: [(-_A, -_A), (0, 0), (_A, _A)],
    4: [(-_A, -_A), (-_A, _A), (_A, -_A), (_A, _A)],
    5: [(-_A, -_A), (-_A, _A), (0, 0), (_A, -_A), (_A, _A)],
    6: [(-_A, -_A), (-_A, 0), (-_A, _A), (_A, -_A), (_A, 0), (_A, _A)],
}


def _skin(skin):
    if skin not in SKINS:
        raise ValueError(f"Неизвестный скин куба: {skin!r}")
    return SKINS[skin]


def face_names(skin):
    """{грань: название} - то, что генератор заданий показывает как варианты."""
    return {face: name for face, (name, _) in _skin(skin)["faces"].items()}


def face_color(skin, face):
    return _skin(skin)["faces"][face][1]


def has_pips(skin):
    return _skin(skin).get("pips", False)


def shows_marks(skin, marks_enabled):
    """Рисовать ли букву на гранях: по настройке или всегда (для дальтоников)."""
    return marks_enabled or _skin(skin).get("always_marks", False)


def face_mark(skin, face):
    """Метка на грани: две первые буквы названия цвета (КР, ОР, БЕ, ЖЁ, СИ, ЗЕ).
    Одна буква не годится: «З» (зелёный) на кубе легко принять за цифру 3."""
    return face_names(skin)[face][:2].upper()


def pips_word(count):
    """1 точка, 2 точки, 5 точек."""
    if count == 1:
        return "точка"
    if count in (2, 3, 4):
        return "точки"
    return "точек"


def option_text(skin, name):
    """Как подписать вариант ответа на кнопке."""
    if has_pips(skin):
        return f"{name} {pips_word(int(name))}"
    return name.capitalize()


def _feminine(color_name):
    """белый -> белая, синий -> синяя (для фразы «белая грань»)."""
    if color_name.endswith("ий") and not color_name.endswith("кий"):
        return color_name[:-2] + "яя"
    return color_name[:-2] + "ая"


def start_description(skin):
    """Фраза об исходном положении куба."""
    names = face_names(skin)
    top, front = names["+Y"], names["-Z"]
    if has_pips(skin):
        return f"Сверху {top} {pips_word(int(top))}, спереди {front} {pips_word(int(front))}"
    return f"Сверху {_feminine(top)} грань, спереди {_feminine(front)}"
