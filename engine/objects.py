from ursina import *
from ursina.shaders import unlit_shader
from core import settings
from logic import cube_skins
from logic.rotations import IDENTITY, rotate


def _mark_color(hex_color):
    """Цвет буквы на грани: тёмная на светлом фоне, белая на тёмном."""
    c = color.hex(hex_color)
    brightness = 0.299 * c.r + 0.587 * c.g + 0.114 * c.b
    return "#0b1220" if brightness > 0.55 else "#f8fafc"


class ColoredCube(Entity):
    """Куб с цветными гранями. Точная ориентация хранится в self.orientation
    (математика из logic/rotations.py), а Ursina лишь показывает её на экране.

    skin - вид граней (см. logic/cube_skins.py): цвета, палитра для
    дальтоников или игральная кость. marks=True - буквы на гранях."""

    # Для каждой грани: позиция наклейки и поворот, при котором её лицевая
    # сторона смотрит наружу (у плоских объектов Ursina лицо смотрит на -Z)
    FACES = {
        "+X": (Vec3(0.5, 0, 0), Vec3(0, -90, 0)),
        "-X": (Vec3(-0.5, 0, 0), Vec3(0, 90, 0)),
        "+Y": (Vec3(0, 0.5, 0), Vec3(90, 0, 0)),
        "-Y": (Vec3(0, -0.5, 0), Vec3(-90, 0, 0)),
        "+Z": (Vec3(0, 0, 0.5), Vec3(0, 180, 0)),
        "-Z": (Vec3(0, 0, -0.5), Vec3(0, 0, 0)),
    }

    COLOR_NAMES = settings.FACE_COLOR_NAMES   # названия граней скина «Цвета»

    def __init__(self, skin="classic", marks=False, **kwargs):
        super().__init__(**kwargs)
        self.busy = False              # True, пока идёт анимация поворота
        self.orientation = IDENTITY    # точная ориентация (матрица 3x3)

        # Тёмное ядро куба
        Entity(parent=self, model="cube", color=color.hex(settings.CUBE_CORE),
               scale=0.98)

        for face, (position, rotation) in self.FACES.items():
            # «Рамка» грани: всё, что на ней нарисовано, лежит в её плоскости
            frame = Entity(parent=self, position=position * 1.002, rotation=rotation)
            hex_color = cube_skins.face_color(skin, face)
            Entity(parent=frame, model="quad", color=color.hex(hex_color),
                   scale=0.9, double_sided=True)
            if cube_skins.has_pips(skin):
                count = int(cube_skins.face_names(skin)[face])
                for px, py in cube_skins.PIP_LAYOUT[count]:
                    Entity(parent=frame, model="circle", scale=0.15,
                           position=(px * 0.9, py * 0.9, -0.004),
                           color=color.hex("#1e293b"), shader=unlit_shader)
            elif cube_skins.shows_marks(skin, marks):
                Text(cube_skins.face_mark(skin, face), parent=frame, origin=(0, 0),
                     position=(0, 0, -0.004), scale=15, shader=unlit_shader,
                     color=color.hex(_mark_color(hex_color)))

    def reset(self):
        """Вернуть куб в исходное положение (когда он не анимируется)."""
        self.orientation = IDENTITY
        self.rotation = Vec3(0, 0, 0)

    def rotate_world(self, axis, angle, on_done=None):
        """Повернуть куб на angle градусов вокруг мировой оси 'x', 'y' или 'z'.
        on_done вызывается, когда анимация закончилась.
        Возвращает True, если поворот принят, и False, если куб ещё занят."""
        if self.busy:
            return False
        self.busy = True

        # 1) Обновляем точную ориентацию (логика)
        self.orientation = rotate(self.orientation, axis, angle)

        # 2) Показываем поворот на экране (с поправкой на знак оси)
        visual_angle = angle * settings.AXIS_SIGN[axis]
        pivot = Entity(position=self.world_position)  # временный шарнир
        self.world_parent = pivot
        pivot.animate(f"rotation_{axis}", visual_angle,
                      duration=settings.ROTATION_DURATION,
                      curve=curve.in_out_cubic)
        invoke(self._finish_rotation, pivot, axis, visual_angle, on_done,
               delay=settings.ROTATION_DURATION + 0.02)
        return True

    def _finish_rotation(self, pivot, axis, visual_angle, on_done):
        # Ставим точный конечный угол: если кадр «подвис», анимация могла
        # не успеть дойти до конца, и куб остался бы повёрнутым не до конца.
        setattr(pivot, f"rotation_{axis}", visual_angle)
        self.world_parent = scene
        destroy(pivot)
        self.busy = False
        if on_done:
            on_done()

    def play_moves(self, moves, on_done=None, pause=0.15):
        """Показать повороты по очереди. Следующий поворот начинается только
        после окончания предыдущего, поэтому ни один не потеряется, даже
        если компьютер на мгновение «подвиснет»."""
        moves = list(moves)
        if not moves:
            if on_done:
                on_done()
            return
        axis, angle = moves[0]

        def next_move():
            invoke(self.play_moves, moves[1:], on_done, pause, delay=pause)

        self.rotate_world(axis, angle, on_done=next_move)


class ShapeView(Entity):
    """Фигура из кубиков по набору клеток (см. logic/shapes.py).
    Фигура центрируется относительно своей позиции."""

    def __init__(self, cells, cube_color, clickable=False, **kwargs):
        super().__init__(**kwargs)
        self.cubes = []
        max_x = max(c[0] for c in cells)
        max_y = max(c[1] for c in cells)
        max_z = max(c[2] for c in cells)
        for x, y, z in cells:
            # collider нужен, чтобы по кубику можно было кликнуть мышью
            self.cubes.append(Entity(parent=self, model="cube", color=color.hex(cube_color),
                                     position=(x - max_x / 2, y - max_y / 2, z - max_z / 2),
                                     scale=0.94, collider="box" if clickable else None))

    def set_color(self, hex_color):
        for cube in self.cubes:
            cube.color = color.hex(hex_color)

    def contains(self, entity):
        """Принадлежит ли entity (например, кубик под курсором) этой фигуре."""
        return entity in self.cubes


class ShadedShape(Entity):
    """Фигура из кубиков для слоя интерфейса (camera.ui). Там нет освещения,
    поэтому грани каждого кубика закрашены разными оттенками - так фигура
    всё равно выглядит объёмной."""

    # Грань: (позиция, поворот, яркость)
    FACES = [
        (Vec3(0, 0.5, 0), Vec3(90, 0, 0), 1.0),      # верх - самый светлый
        (Vec3(0, -0.5, 0), Vec3(-90, 0, 0), 0.45),
        (Vec3(0, 0, -0.5), Vec3(0, 0, 0), 0.8),      # перед
        (Vec3(0, 0, 0.5), Vec3(0, 180, 0), 0.6),
        (Vec3(0.5, 0, 0), Vec3(0, -90, 0), 0.65),
        (Vec3(-0.5, 0, 0), Vec3(0, 90, 0), 0.7),
    ]

    def __init__(self, cells, hex_color, **kwargs):
        super().__init__(parent=kwargs.pop("parent", camera.ui), **kwargs)
        base = color.hex(hex_color)
        center = [(max(c[i] for c in cells) + min(c[i] for c in cells)) / 2
                  for i in range(3)]
        for cell in cells:
            cube = Entity(parent=self, scale=0.92,
                          position=tuple(cell[i] - center[i] for i in range(3)))
            for position, rotation, light in self.FACES:
                Entity(parent=cube, model="quad", position=position, rotation=rotation,
                       color=color.rgba(base.r * light, base.g * light, base.b * light, 1),
                       shader=unlit_shader, double_sided=True)


class ShadedBlock(Entity):
    """Кубик постройки: тёмное ядро и грани разной яркости (верх светлее,
    низ темнее), поэтому кубики хорошо читаются и между ними видны швы.
    Коллайдер нужен, чтобы мышь могла попасть в кубик и его грани."""

    def __init__(self, hex_color, **kwargs):
        super().__init__(model="cube", color=color.hex(settings.CUBE_CORE),
                         scale=0.98, collider="box", **kwargs)
        self.faces = []
        for position, rotation, light in ShadedShape.FACES:
            self.faces.append(Entity(parent=self, model="quad", scale=0.9,
                                     position=position * 1.004, rotation=rotation,
                                     shader=unlit_shader, double_sided=True))
            self.faces[-1].light = light
        self.set_color(hex_color)

    def set_color(self, hex_color):
        base = color.hex(hex_color)
        for face in self.faces:
            face.color = color.rgba(base.r * face.light, base.g * face.light,
                                    base.b * face.light, 1)


def dispose(entity):
    """Удалить объект вместе со всеми вложенными (дочерними) объектами."""
    for child in list(entity.children):   # list(...) - копия, т.к. список меняется
        dispose(child)
    destroy(entity)