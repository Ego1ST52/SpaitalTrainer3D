from ursina import *


class CameraRig:
    """Камера: правая кнопка мыши вращает, колесо приближает."""

    def __init__(self):
        self.control = EditorCamera()
        self.control.move_speed = 0

    def view(self, position, pitch):
        """Поставить камеру в начальный ракурс."""
        self.control.position = (0, 0, 0)
        self.control.rotation = Vec3(pitch, 0, 0)
        camera.position = position
        # EditorCamera каждый кадр плавно тянет камеру к своей цели target_z
        # (так работает приближение колесом). Если цель не обновить,
        # камера «уедет» обратно на старое расстояние.
        self.control.target_z = camera.z
