"""Личные настройки игрока. Без Ursina и без базы: только значения и проверка.

У каждого игрока свои настройки (хранятся в базе, см. data/database.py).
`prefs` ниже - настройки ТЕКУЩЕГО игрока; main.py загружает их при
выборе игрока, а экраны просто читают, например, prefs.get("cube_skin").
"""

import copy

from logic.assessment import validate_assessment
from logic.playlist import validate_plan
from logic.theme import parse_color


def _validate_plan_dict(value):
    if not isinstance(value, dict):
        raise ValueError("Набор тренировки должен быть словарём")
    validate_plan(value)


def _validate_seen(value):
    """Список режимов, подсказку к которым игрок уже видел."""
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError("Список просмотренных подсказок должен быть списком строк")


def _validate_theme(value):
    """Тема: "" (стандартная) или цвет '#rrggbb'."""
    if value != "" and (not isinstance(value, str) or parse_color(value) != value):
        raise ValueError(f"Неверный цвет темы: {value!r}")

# Режимы-стройки: собирать дольше, чем выбирать ответ
BUILD_MODES = ("construction", "memory", "symmetry", "views")

# Для каждой настройки: допустимые значения (первое - по умолчанию не обязательно)
OPTIONS = {
    "adaptive": (False, True),
    "free_rotation": (False, True),     # вращать куб самому ещё до ответа (подсказка)
    "cube_skin": ("classic", "colorblind", "dice", "neon", "pastel", "jewel"),
    "daily_goal": (0, 10, 20, 30),      # заданий в день (0 - без цели)
    "face_marks": (False, True),
    "session_length": (5, 10, 15, 20),
    "mouse_sensitivity": ("low", "medium", "high"),
    "reduce_motion": (False, True),
    "sound": ("off", "quiet", "loud"),
    "stereo": (False, True),            # красно-синие очки; после перезапуска
}

# Сложные настройки (словари) проверяются функцией, а не списком значений
VALIDATORS = {
    "custom_plan": _validate_plan_dict,   # последний набор из «Моей тренировки»
    "theme": _validate_theme,             # пользовательская тема
    "seen_tutorials": _validate_seen,     # режимы, где уже показана подсказка
    "assessment": validate_assessment,    # итоги входного и итогового теста
}

DEFAULTS = {
    "adaptive": False,
    "free_rotation": False,
    "custom_plan": {"modes": ["rotation", "projection"], "level": "easy", "per_mode": 3,
                    "order": "mixed", "adaptive": True},
    "cube_skin": "classic",
    "daily_goal": 20,
    "theme": "",
    "seen_tutorials": [],
    "assessment": {},
    "face_marks": False,
    "session_length": 10,
    "mouse_sensitivity": "medium",
    "reduce_motion": False,
    "sound": "quiet",
    "stereo": False,
}

SENSITIVITY_FACTOR = {"low": 0.6, "medium": 1.0, "high": 1.6}


class Preferences:
    def __init__(self, values=None):
        self.saver = None       # функция (ключ, значение) -> сохранить в базе; см. main.py
        self._values = copy.deepcopy(DEFAULTS)
        if values:
            self.load(values)

    def get(self, key):
        # Копия, чтобы случайно не изменить настройку в обход set()
        return copy.deepcopy(self._values[key])

    def set(self, key, value):
        """Изменить настройку. Недопустимое значение - ошибка."""
        if key in VALIDATORS:
            VALIDATORS[key](value)
        elif key not in OPTIONS:
            raise KeyError(f"Неизвестная настройка: {key!r}")
        elif value not in OPTIONS[key]:
            raise ValueError(f"Недопустимое значение {value!r} для {key!r}")
        self._values[key] = copy.deepcopy(value)

    def save(self, key, value):
        """Изменить настройку и сразу сохранить её (если задан saver)."""
        self.set(key, value)
        if self.saver is not None:
            self.saver(key, value)

    def load(self, values):
        """Сбросить к значениям по умолчанию и взять из values всё допустимое.
        Неизвестные ключи и испорченные значения молча пропускаются, чтобы
        повреждённая запись в базе не ломала запуск игры."""
        self._values = copy.deepcopy(DEFAULTS)
        for key, value in values.items():
            try:
                self.set(key, value)
            except (KeyError, ValueError):
                pass

    def as_dict(self):
        return copy.deepcopy(self._values)

    # ---------- удобные производные значения ----------
    @property
    def sensitivity_factor(self):
        return SENSITIVITY_FACTOR[self.get("mouse_sensitivity")]

    @property
    def reduce_motion(self):
        return self.get("reduce_motion")

    def session_length(self, mode):
        """Сколько заданий в тренировке. Сборка дольше - заданий вдвое меньше."""
        length = self.get("session_length")
        return max(3, length // 2) if mode in BUILD_MODES else length


# Настройки текущего игрока (один объект на всё приложение)
prefs = Preferences()
