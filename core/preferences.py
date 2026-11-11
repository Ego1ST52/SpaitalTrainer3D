"""Личные настройки игрока. Без Ursina и без базы: только значения и проверка.

У каждого игрока свои настройки (хранятся в базе, см. data/database.py).
`prefs` ниже - настройки ТЕКУЩЕГО игрока; main.py загружает их при
выборе игрока, а экраны просто читают, например, prefs.get("cube_skin").
"""

# Для каждой настройки: допустимые значения (первое - по умолчанию не обязательно)
OPTIONS = {
    "cube_skin": ("classic", "colorblind", "dice"),
    "face_marks": (False, True),
    "session_length": (5, 10, 15, 20),
    "mouse_sensitivity": ("low", "medium", "high"),
    "reduce_motion": (False, True),
}

DEFAULTS = {
    "cube_skin": "classic",
    "face_marks": False,
    "session_length": 10,
    "mouse_sensitivity": "medium",
    "reduce_motion": False,
}

SENSITIVITY_FACTOR = {"low": 0.6, "medium": 1.0, "high": 1.6}


class Preferences:
    def __init__(self, values=None):
        self._values = dict(DEFAULTS)
        if values:
            self.load(values)

    def get(self, key):
        return self._values[key]

    def set(self, key, value):
        """Изменить настройку. Недопустимое значение - ошибка."""
        if key not in OPTIONS:
            raise KeyError(f"Неизвестная настройка: {key!r}")
        if value not in OPTIONS[key]:
            raise ValueError(f"Недопустимое значение {value!r} для {key!r}")
        self._values[key] = value

    def load(self, values):
        """Сбросить к значениям по умолчанию и взять из values всё допустимое.
        Неизвестные ключи и испорченные значения молча пропускаются, чтобы
        повреждённая запись в базе не ломала запуск игры."""
        self._values = dict(DEFAULTS)
        for key, value in values.items():
            try:
                self.set(key, value)
            except (KeyError, ValueError):
                pass

    def as_dict(self):
        return dict(self._values)

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
