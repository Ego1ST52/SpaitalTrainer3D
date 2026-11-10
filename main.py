import os
from ursina import *
from ursina.lights import DirectionalLight, AmbientLight
from ursina.shaders import lit_with_shadows_shader

from core import settings
from core.scene_manager import SceneManager
from engine.camera import CameraRig
from interface.main_menu import MainMenu
from interface.game_interface import RotationGameScreen
from interface.matching_interface import MatchingGameScreen

app = Ursina(title=settings.WINDOW_TITLE)
window.color = color.hex(settings.BACKGROUND)
window.fps_counter.enabled = settings.SHOW_FPS

if os.path.exists(settings.FONT_PATH):
    Text.default_font = settings.FONT_PATH

Entity.default_shader = lit_with_shadows_shader

sun = DirectionalLight(shadows=True)
sun.look_at(Vec3(1, -1.5, 1))
AmbientLight(color=color.rgba(110, 110, 130, 0.1))

rig = CameraRig()
manager = SceneManager()


def open_menu():
    rig.view((0, 0, -20), 0)
    return MainMenu(manager)


def open_rotation(level="easy"):
    rig.view((0, 2, -8), 15)
    return RotationGameScreen(manager, level)


def open_matching(level="easy"):
    rig.view((0, 1, -24), 10)
    return MatchingGameScreen(manager, level)


manager.register("menu", open_menu)
manager.register("rotation", open_rotation)
manager.register("matching", open_matching)

manager.go("menu")
app.run()