import os
import sqlite3

from ursina import *
from ursina.lights import DirectionalLight, AmbientLight
from ursina.shaders import lit_with_shadows_shader

from core import settings
from core.scene_manager import SceneManager
from data.database import Database
from engine.backdrop import Backdrop
from engine.camera import CameraRig
from interface.main_menu import MainMenu
from interface.game_interface import RotationGameScreen
from interface.matching_interface import MatchingGameScreen
from interface.projection_interface import ProjectionGameScreen
from interface.construction_interface import ConstructionGameScreen
from interface.results_screen import ResultsScreen
from interface.statistics_screen import StatisticsScreen
from interface.progress_screen import ProgressScreen

app = Ursina(title=settings.WINDOW_TITLE, borderless=False)
window.color = color.hex(settings.BACKGROUND)
# Служебные счётчики Ursina (кадры, объекты) показываем только для отладки
window.editor_ui.enabled = settings.SHOW_FPS

if os.path.exists(settings.FONT_PATH):
    Text.default_font = settings.FONT_PATH

Entity.default_shader = lit_with_shadows_shader

sun = DirectionalLight(shadows=True)
sun.look_at(Vec3(1, -1.5, 1))
AmbientLight(color=color.rgba32(110, 110, 130))   # rgba32: значения 0..255

# База данных. Если она недоступна, игра всё равно работает.
try:
    db = Database(settings.DB_PATH)
    user_id = db.get_or_create_user(settings.DEFAULT_USER)
except (sqlite3.Error, OSError) as error:
    print("База данных недоступна:", error)
    db = None
    user_id = None

rig = CameraRig()
Backdrop()   # фон-свечение позади всех объектов
manager = SceneManager()


def load_history():
    """История тренировок или None, если база недоступна."""
    if db is None:
        return None
    try:
        return db.get_history(user_id)
    except sqlite3.Error as error:
        print("Не удалось прочитать историю:", error)
        return None


def open_menu():
    rig.view((0, 0, -20), 0, interactive=False)
    return MainMenu(manager, load_history())


def open_rotation(level="easy"):
    rig.view((0, 0, -11), 22)
    return RotationGameScreen(manager, level)


def open_matching(level="easy"):
    # Камера закреплена: правая кнопка мыши вращает сами фигуры (см. SyncRotator),
    # иначе фигуры поменялись бы местами и ушли со своих кнопок.
    rig.view((0, 0, -24), 0, interactive=False)
    return MatchingGameScreen(manager, level)


def open_projection(level="easy"):
    rig.view((0, 0, -24), 0, interactive=False)
    return ProjectionGameScreen(manager, level)


def open_construction(level="easy"):
    # Камера свободная: правой кнопкой мыши можно обойти стройку со всех сторон
    # x = 1.8: камера чуть правее центра, поэтому стройка видна левее правой панели
    rig.view((1.8, 0, -17), 35)
    return ConstructionGameScreen(manager, level)


def open_results(session):
    saved = False
    if db is not None:
        try:
            db.save_session(user_id, session)
            saved = True
        except (sqlite3.Error, ValueError) as error:
            print("Не удалось сохранить результат:", error)
    rig.view((0, 0, -20), 0, interactive=False)
    return ResultsScreen(manager, session, saved)


def open_statistics():
    rig.view((0, 0, -20), 0, interactive=False)
    return StatisticsScreen(manager, load_history())


def open_progress():
    rig.view((0, 0, -20), 0, interactive=False)
    return ProgressScreen(manager, load_history())


manager.register("menu", open_menu)
manager.register("rotation", open_rotation)
manager.register("matching", open_matching)
manager.register("projection", open_projection)
manager.register("construction", open_construction)
manager.register("results", open_results)
manager.register("statistics", open_statistics)
manager.register("progress", open_progress)

manager.go("menu")
app.run()