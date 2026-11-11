from ursina import *

from core.preferences import prefs


class SyncRotator:
    """Правая кнопка мыши поворачивает сразу несколько объектов - каждый
    вокруг своего центра и все на один и тот же угол.

    Зачем: в режимах с несколькими фигурами нельзя вращать камеру - тогда
    поворачивается вся сцена, фигуры меняются местами и уже не стоят над
    своими кнопками. А одинаковый поворот всех фигур не меняет ответ:
    одинаковые фигуры остаются одинаковыми."""

    SPEED = 200        # градусов на полный проход мыши по экрану

    def __init__(self, start_pitch=22, start_yaw=-32):
        self.start = (start_pitch, start_yaw)
        self.pitch, self.yaw = self.start
        self.targets = []

    def set_targets(self, entities):
        self.targets = list(entities)
        self._apply()

    def reset(self):
        """Вернуть исходный ракурс."""
        self.pitch, self.yaw = self.start
        self._apply()

    def update(self):
        """Вызывать каждый кадр из update() экрана."""
        if held_keys["right mouse"]:
            speed = self.SPEED * prefs.sensitivity_factor      # из настроек игрока
            self.yaw -= mouse.velocity[0] * speed
            # наклон ограничен, чтобы фигура не переворачивалась «через голову»
            self.pitch = clamp(self.pitch + mouse.velocity[1] * speed, -85, 85)
            self._apply()

    def _apply(self):
        for entity in self.targets:
            entity.rotation = Vec3(self.pitch, self.yaw, 0)
