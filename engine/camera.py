from ursina import *

from core.preferences import prefs


class CameraRig:
    """Камера: правая кнопка мыши вращает, колесо приближает."""

    ROTATION_SPEED = 200
    ZOOM_SPEED = 1.25
    PAN_SPEED = Vec2(5, 5)

    def __init__(self):
        self.control = EditorCamera()
        self.control.move_speed = 0

    def view(self, position, pitch, interactive=True):
        """Поставить камеру в начальный ракурс.
        interactive=False - камера закреплена (меню и прочие экраны с
        интерфейсом): иначе 3D-объекты уезжают под кнопки camera.ui."""
        self.control.ignore_input = not interactive
        speed = self.ROTATION_SPEED * prefs.sensitivity_factor   # из настроек игрока
        self.control.rotation_speed = speed if interactive else 0
        self.control.zoom_speed = self.ZOOM_SPEED if interactive else 0
        self.control.pan_speed = self.PAN_SPEED if interactive else Vec2(0, 0)
        self.control.position = (0, 0, 0)
        self.control.rotation = Vec3(pitch, 0, 0)
        camera.position = position
        # EditorCamera каждый кадр плавно тянет камеру к своей цели target_z
        # (так работает приближение колесом). Если цель не обновить,
        # камера «уедет» обратно на старое расстояние.
        self.control.target_z = camera.z
