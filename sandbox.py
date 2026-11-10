import os
from ursina import *
from ursina.lights import DirectionalLight, AmbientLight
from ursina.shaders import lit_with_shadows_shader

from core import settings
from engine.objects import ColoredCube
from logic.rotations import face_at

app = Ursina(title=settings.WINDOW_TITLE)
window.color = color.hex(settings.BACKGROUND)

if os.path.exists(settings.FONT_PATH):
    Text.default_font = settings.FONT_PATH

Entity.default_shader = lit_with_shadows_shader

sun = DirectionalLight(shadows=True)
sun.look_at(Vec3(1, -1.5, 1))
AmbientLight(color=color.rgba(110, 110, 130, 0.1))

floor = Entity(model="plane", scale=14, y=-1.5,
               color=color.hex(settings.FLOOR_COLOR))

cube = ColoredCube()

camera_control = EditorCamera()
camera_control.move_speed = 0
camera.position = (0, 2, -8)
camera_control.rotation_x = 15

Text("Стрелки: поворот вокруг осей X и Y   Z / X: вокруг оси Z\n"
     "Правая кнопка мыши: вращать камеру   Колесо: масштаб",
     position=window.top_left + Vec2(0.02, -0.02),
     color=color.hex(settings.TEXT_COLOR), scale=1)

# Строка проверки: что куб "должен" показывать по расчёту логики
status = Text("", position=window.bottom_left + Vec2(0.02, 0.06),
              color=color.hex(settings.ACCENT), scale=1.2)


def update_status():
    def color_name(direction):
        return cube.COLOR_NAMES[face_at(cube.orientation, direction)]
    status.text = (f"По расчёту: верх - {color_name('+Y')}, "
                   f"спереди - {color_name('-Z')}, "
                   f"справа - {color_name('+X')}")


def turn(axis, angle):
    if cube.rotate_world(axis, angle):
        update_status()


def input(key):
    if key == "right arrow":
        turn("y", -90)
    elif key == "left arrow":
        turn("y", 90)
    elif key == "up arrow":
        turn("x", 90)
    elif key == "down arrow":
        turn("x", -90)
    elif key == "z":
        turn("z", 90)
    elif key == "x":
        turn("z", -90)


update_status()
app.run()