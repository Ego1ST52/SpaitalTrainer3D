"""3D-куб главного меню. Какая грань спереди, решает logic/cube_nav.py,
а этот модуль только показывает куб и плавно поворачивает его.

Устройство (от внешнего к внутреннему):
  self        - «витрина»: лёгкий наклон, покачивание, реакция на мышь;
  pitch_pivot - наклон вверх/вниз (показать верхнюю или нижнюю грань);
  yaw_pivot   - поворот пояса влево/вправо;
  frames      - шесть граней, на каждой своё содержимое.
"""

import math

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from core.preferences import prefs

SIZE = 4.0                 # ребро куба (единицы сцены)
CONTENT_SCALE = 10         # содержимое грани строится в «единицах интерфейса» x10
TURN_SECONDS = 0.45
BASE_TILT = Vec3(-13, 20, 0)   # наклон витрины: видны края верхней и правой граней

# Место грани на кубе и поворот её «рамки», при котором лицо смотрит наружу
FACE_PLACES = {
    "front": (Vec3(0, 0, -1), Vec3(0, 0, 0)),
    "right": (Vec3(1, 0, 0), Vec3(0, -90, 0)),
    "back": (Vec3(0, 0, 1), Vec3(0, 180, 0)),
    "left": (Vec3(-1, 0, 0), Vec3(0, 90, 0)),
    "top": (Vec3(0, 1, 0), Vec3(90, 0, 0)),
    "bottom": (Vec3(0, -1, 0), Vec3(-90, 0, 0)),
}


def mouse_position():
    """Позиция мыши на экране или (0, 0), если у окна нет указателя
    (так бывает в автотестах, где окно не показывается)."""
    try:
        return Vec2(mouse.x, mouse.y)
    except AttributeError:
        return Vec2(0, 0)


class NavCube(Entity):
    def __init__(self, yaw=0, pitch=0, **kwargs):
        super().__init__(**kwargs)
        self.rotation = BASE_TILT
        self.base_y = self.y
        self.pitch_pivot = Entity(parent=self)
        self.yaw_pivot = Entity(parent=self.pitch_pivot)
        self.yaw_turns = yaw          # сколько четвертей пройдено (может быть любым)
        self.frames = {}              # грань -> рамка
        self.contents = {}            # грань -> содержимое (его поворачиваем «по месту»)

        # Тёмное ядро куба
        Entity(parent=self.yaw_pivot, model="cube", scale=SIZE * 0.985,
               color=color.hex("#0a1222"), shader=unlit_shader)

        for face, (direction, rotation) in FACE_PLACES.items():
            # Верх и низ крепим к поясу тоже: куб вращается целиком, как настоящий
            frame = Entity(parent=self.yaw_pivot, position=direction * (SIZE / 2 + 0.01),
                           rotation=rotation)
            frame.face_name = face
            content = Entity(parent=frame, scale=CONTENT_SCALE)
            content.face_name = face
            self.frames[face] = frame
            self.contents[face] = content

        self.set_state(yaw, pitch, animate=False)

    # ---------- повороты ----------
    def set_state(self, yaw_turns, pitch, animate=True):
        """Повернуть куб: yaw_turns - четверти по поясу, pitch - 0/1/-1."""
        self.yaw_turns = yaw_turns
        yaw_angle = 90 * yaw_turns
        pitch_angle = -90 * pitch        # -90: верхняя грань поворачивается к нам
        if animate and not prefs.reduce_motion:
            self.yaw_pivot.animate("rotation_y", yaw_angle, duration=TURN_SECONDS,
                                   curve=curve.out_cubic)
            self.pitch_pivot.animate("rotation_x", pitch_angle, duration=TURN_SECONDS,
                                     curve=curve.out_cubic)
        else:
            self.yaw_pivot.rotation_y = yaw_angle
            self.pitch_pivot.rotation_x = pitch_angle
        # Текст на верхней/нижней грани должен читаться ровно при любом поясе
        for face in ("top", "bottom"):
            roll = self._upright_roll(face, yaw_angle, pitch_angle)
            content = self.contents[face]
            if animate and not prefs.reduce_motion:
                content.animate("rotation_z", roll, duration=TURN_SECONDS, curve=curve.out_cubic)
            else:
                content.rotation_z = roll

    def _upright_roll(self, face, yaw_angle, pitch_angle):
        """Поворот содержимого грани вокруг её оси, при котором «верх» текста
        будет смотреть вверх, когда грань окажется спереди. Не угадываем знаки,
        а проверяем четыре варианта на невидимой копии.
        Ближайший к текущему вращению вариант выбираем, чтобы не крутить лишнее."""
        _, rotation = FACE_PLACES[face]
        pitch = Entity(rotation_x=pitch_angle, add_to_scene_entities=False)
        yaw = Entity(parent=pitch, rotation_y=yaw_angle, add_to_scene_entities=False)
        frame = Entity(parent=yaw, rotation=rotation, add_to_scene_entities=False)
        probe = Entity(parent=frame, add_to_scene_entities=False)
        best, best_up = 0, -2
        current = self.contents[face].rotation_z
        for k in range(4):
            roll = round(current / 90) * 90 + 90 * k
            probe.rotation_z = roll
            up = probe.up.y
            if up > best_up + 1e-6:
                best, best_up = roll, up
        for e in (probe, frame, yaw, pitch):
            e.removeNode()
        return best

    # ---------- жизнь куба ----------
    def update(self):
        if prefs.reduce_motion:
            return
        # Лёгкое покачивание и наклон вслед за мышью - куб «живой»
        t = time.time()
        self.y = self.base_y + math.sin(t * 1.2) * 0.08
        pointer = mouse_position()
        target = BASE_TILT + Vec3(pointer.y * 10, pointer.x * 14, 0)
        self.rotation = lerp(self.rotation, target, min(1, time.dt * 3))

    def face_of(self, entity):
        """Какой грани принадлежит entity (например, то, что под курсором)."""
        while entity is not None and entity is not scene:
            name = getattr(entity, "face_name", None)
            if name:
                return name
            entity = entity.parent
        return None
