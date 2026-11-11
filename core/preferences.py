"""Личные настройки игрока. Без Ursina и без базы: только значения и проверка.

У каждого игрока свои настройки (хранятся в базе, см. data/database.py).
`prefs` ниже - настройки ТЕКУЩЕГО игрока; main.py загружает их при
выборе игрока, а экраны просто читают, например, prefs.get("cube_skin").
"""

import copy

from logic.playlist import validate_plan

# Для каждой настройки: допустимые значения (первое - по умолчанию не обязательно)
OPTIONS = {
    "adaptive": (False, True),
    "cube_skin": ("classic", "colorblind", "dice"),
    "face_marks": (False, True),
    "session_length": (5, 10, 15, 20),
    "mouse_sensitivity": ("low", "medium", "high"),
    "reduce_motion": (False, True),
}

# Сложные настройки (словари) проверяются функцией, а не списком значений
VALIDATORS = {
    "custom_plan": validate_plan,     # последний набор из «Моей тренировки»
}

DEFAULTS = {
    "adaptive": False,
    "custom_plan": {"modes": ["rotation", "projection"], "level": "easy", "per_mode": 3,
                    "order": "mixed", "adaptive": True},
    "cube_skin": "classic",
    "face_marks": False,
    "session_length": 10,
    "mouse_sensitivity": "medium",
    "reduce_motion": False,
}

SENSITIVITY_FACTOR = {"low": 0.6, "medium": 1.0, "high": 1.6}


class Preferences:
    def __init__(self, values=None):
        self._values = copy.deepcopy(DEFAULTS)
        if values:
            self.load(values)

    def get(self, key):
        # Копия, чтобы случайно не изменить настройку в обход set()
        return copy.deepcopy(self._values[key])

    def set(self, key, value):
        """Изменить настройку. Недопустимое значение - ошибка."""
        if key in VALIDATORS:
            if not isinstance(value, dict):
                raise ValueError(f"Недопустимое значение {value!r} для {key!r}")
            VALIDATORS[key](value)
        elif key not in OPTIONS:
            raise KeyError(f"Неизвестная настройка: {key!r}")
        elif value not in OPTIONS[key]:
            raise ValueError(f"Недопустимое значение {value!r} для {key!r}")
        self._values[key] = copy.deepcopy(value)

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
        return max(3, length // 2) if mode == "construction" else length


# Настройки текущего игрока (один объект на всё приложение)
prefs = Preferences()
