"""Режим «Тень»: лампа светит на фигуру - какая тень упадёт на стену или пол?"""

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.objects import ShapeView
from interface.choice_screen import ChoiceGameScreen, draw_picture
from interface.layout3d import fit_scale
from logic.shadows import ShadowTaskGenerator

LAMP_DISTANCE = 4.0
WALL_DISTANCE = 2.6
WALL_SIZE = 4.0
SCENE_POSITION = Vec3(-0.6, 0, 0)
SHAPE_MAX_SIZE = 2.6

# Для каждой стороны света: где лампа, где стена, как стена повёрнута к фигуре
# и как повернуть всю сцену, чтобы стена с тенью смотрела на зрителя
SIDES = {
    "left": {"lamp": Vec3(-LAMP_DISTANCE, 0.3, 0), "axis": 0, "sign": 1,
             "wall_rotation": Vec3(0, 90, 0), "scene_yaw": -45},
    "right": {"lamp": Vec3(LAMP_DISTANCE, 0.3, 0), "axis": 0, "sign": -1,
              "wall_rotation": Vec3(0, -90, 0), "scene_yaw": 45},
    "front": {"lamp": Vec3(1.6, -0.9, -LAMP_DISTANCE), "axis": 2, "sign": 1,
              "wall_rotation": Vec3(0, 0, 0), "scene_yaw": -15},
    "top": {"lamp": Vec3(0, LAMP_DISTANCE, 0), "axis": 1, "sign": -1,
            "wall_rotation": Vec3(90, 0, 0), "scene_yaw": -20},
}


class ShadowGameScreen(ChoiceGameScreen):
    MODE = "shadow"
    HINT = "Свет от лампы параллельный, как от солнца"

    def make_generator(self, seed):
        return ShadowTaskGenerator(seed=seed)

    def build_scene(self):
        cells = self.task.shape
        self.shape_scale = fit_scale(cells, SHAPE_MAX_SIZE)
        side = SIDES[self.task.view]
        self.scene = Entity(position=SCENE_POSITION, rotation_y=side["scene_yaw"])
        ShapeView(cells, self.accent, parent=self.scene, scale=self.shape_scale)

        # Лампа: светящийся шар и мягкий ореол вокруг
        Entity(parent=self.scene, model="sphere", scale=0.4, position=side["lamp"],
               color=color.hex("#fde68a"), shader=unlit_shader)
        Entity(parent=self.scene, model="circle", scale=0.9, position=side["lamp"],
               billboard=True, color=color.rgba(1, 0.9, 0.5, 0.15), shader=unlit_shader)

        # Стена (или пол) напротив лампы, с сеткой
        wall_position = Vec3(0, 0, 0)
        wall_position[side["axis"]] = side["sign"] * WALL_DISTANCE
        self.wall_position = wall_position
        wall = Entity(parent=self.scene, position=wall_position, rotation=side["wall_rotation"])
        Entity(parent=wall, model="quad", scale=WALL_SIZE, shader=unlit_shader,
               color=color.hex(settings.SURFACE_HOVER), double_sided=True)
        Entity(parent=wall, model=Grid(8, 8), scale=WALL_SIZE, z=-0.005, shader=unlit_shader,
               color=color.hex(settings.BORDER))
        self.wall = wall
        self.task_objects.append(self.scene)

    def subtitle_text(self):
        return "Тень - это вид фигуры со стороны лампы"

    def draw_option(self, index, option, card):
        draw_picture(card, option, settings.TEXT_COLOR)

    def after_answer(self, correct):
        """Настоящая тень на стене: каждый кубик отбрасывает квадрат вдоль луча."""
        cells = self.task.shape
        side = SIDES[self.task.view]
        axis = side["axis"]
        maxima = [max(c[i] for c in cells) for i in range(3)]
        squares = set()
        for cell in cells:
            point = [(cell[i] - maxima[i] / 2) * self.shape_scale for i in range(3)]
            point[axis] = self.wall_position[axis] - side["sign"] * 0.02   # чуть перед стеной
            squares.add(tuple(round(v, 4) for v in point))
        for point in squares:
            Entity(parent=self.scene, model="quad", position=Vec3(*point),
                   rotation=side["wall_rotation"], scale=self.shape_scale * 0.98,
                   color=color.rgba(0.02, 0.03, 0.06, 0.85), shader=unlit_shader,
                   double_sided=True)
