import os
import sqlite3

from ursina import *
from ursina.lights import DirectionalLight, AmbientLight
from ursina.shaders import lit_with_shadows_shader

from core import settings
from core.fonts import setup_input_font
from core.preferences import prefs
from core.theme import apply_theme
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
from interface.settings_screen import SettingsScreen
from interface.profiles_screen import ProfilesScreen
from interface.custom_screen import CustomTrainingScreen
from interface.custom_results_screen import CustomResultsScreen
from interface.achievements_screen import AchievementsScreen
from logic.achievements import newly_unlocked, unlocked_skins

app = Ursina(title=settings.WINDOW_TITLE, borderless=False)
window.color = color.hex(settings.BACKGROUND)
# Служебные счётчики Ursina (кадры, объекты) показываем только для отладки
window.editor_ui.enabled = settings.SHOW_FPS

if os.path.exists(settings.FONT_PATH):
    Text.default_font = settings.FONT_PATH
# Поля ввода (имя игрока, код) рисуются моноширинным шрифтом; встроенный в
# Ursina не знает русских букв, поэтому берём подходящий шрифт из Windows
setup_input_font()

Entity.default_shader = lit_with_shadows_shader

sun = DirectionalLight(shadows=True)
sun.look_at(Vec3(1, -1.5, 1))
AmbientLight(color=color.rgba32(110, 110, 130))   # rgba32: значения 0..255

# База данных. Если она недоступна, игра всё равно работает.
try:
    db = Database(settings.DB_PATH)
except (sqlite3.Error, OSError) as error:
    print("База данных недоступна:", error)
    db = None

# Текущий игрок. Его настройки загружаются в prefs (core/preferences.py).
player = {"id": None, "name": settings.DEFAULT_USER, "color": settings.ACCENT}
backdrop = None      # фон создаётся ниже; тема перерисовывает и его


def apply_current_theme():
    """Перекрасить интерфейс в тему текущего игрока."""
    apply_theme(prefs.get("theme"))
    window.color = color.hex(settings.BACKGROUND)
    if backdrop is not None:
        backdrop.refresh()


def activate_user(user_id):
    """Сделать игрока текущим: загрузить его настройки и запомнить выбор."""
    for user in db.list_users():
        if user["id"] == user_id:
            player.update(id=user_id, name=user["name"], color=user["color"])
            break
    prefs.load(db.get_settings(user_id))
    apply_current_theme()                  # у каждого игрока своя тема
    db.set_state("last_user", user_id)


def start_with_last_user():
    """При запуске выбираем того, кто играл последним (или игрока по умолчанию)."""
    ids = [user["id"] for user in db.list_users()]
    last = db.get_state("last_user")
    activate_user(last if last in ids else db.get_or_create_user(settings.DEFAULT_USER))


if db is not None:
    try:
        start_with_last_user()
    except sqlite3.Error as error:
        print("Не удалось загрузить игрока:", error)

rig = CameraRig()
backdrop = Backdrop()   # фон-свечение позади всех объектов
manager = SceneManager()


def load_history():
    """История тренировок текущего игрока или None, если база недоступна."""
    if db is None or player["id"] is None:
        return None
    try:
        return db.get_history(player["id"])
    except sqlite3.Error as error:
        print("Не удалось прочитать историю:", error)
        return None


# ---------- игроки и настройки ----------
def save_preference(key, value):
    """Изменить настройку текущего игрока и сохранить её в базе."""
    prefs.set(key, value)
    if db is not None and player["id"] is not None:
        try:
            db.set_setting(player["id"], key, value)
        except sqlite3.Error as error:
            print("Не удалось сохранить настройку:", error)


def change_theme(color_value):
    """Новая тема из настроек: сохранить, перекрасить и открыть настройки заново,
    чтобы игрок сразу увидел результат."""
    save_preference("theme", color_value)
    apply_current_theme()
    # Небольшая задержка: нельзя удалять экран прямо во время клика по его кнопке
    invoke(manager.go, "settings", delay=0.05)


def select_user(user_id):
    try:
        activate_user(user_id)
    except sqlite3.Error as error:
        print("Не удалось выбрать игрока:", error)


def create_user(name):
    """Создать игрока и сразу выбрать его. Возвращает текст ошибки или None."""
    try:
        user_id = db.create_user(name)
        activate_user(user_id)
    except ValueError as error:
        return str(error)
    except sqlite3.Error:
        return "Не удалось сохранить игрока в базу данных."
    return None


def list_users():
    if db is None:
        return None
    try:
        return db.list_users()
    except sqlite3.Error:
        return None


# ---------- экраны ----------
def menu_view():
    """Ракурс для экранов с интерфейсом: камера закреплена."""
    rig.view((0, 0, -20), 0, interactive=False)


def open_menu():
    # Меню - куб-навигатор: камера ближе, чем на других экранах, куб крупный
    rig.view((0, 0, -22), 0, interactive=False)
    return MainMenu(manager, load_history(), player)


def open_settings():
    menu_view()
    return SettingsScreen(manager, player["name"], save_preference,
                          unlocked_skins(load_history() or [], prefs.get("daily_goal")),
                          on_theme=change_theme)


def open_achievements():
    menu_view()
    return AchievementsScreen(manager, load_history(), prefs.get("daily_goal"),
                              lambda goal: save_preference("daily_goal", goal))


def save_and_check_achievements(sessions):
    """Сохранить тренировки и узнать, какие достижения получены благодаря им.
    Возвращает (сохранено ли, [новые достижения])."""
    if db is None or player["id"] is None:
        return False, []
    before = load_history() or []
    try:
        for session in sessions:
            db.save_session(player["id"], session)
    except (sqlite3.Error, ValueError) as error:
        print("Не удалось сохранить результат:", error)
        return False, []
    after = load_history() or []
    return True, newly_unlocked(before, after, prefs.get("daily_goal"))


def open_profiles():
    menu_view()
    return ProfilesScreen(manager, list_users(), player["id"], select_user, create_user)


# seed и locked приходят из «тренировки по коду», playlist - из «Моей тренировки»
# (см. interface/game_common.py)
def open_rotation(level="easy", seed=None, locked=False, playlist=None):
    rig.view((0, 0, -11), 22)
    return RotationGameScreen(manager, level, seed, locked, playlist)


def open_matching(level="easy", seed=None, locked=False, playlist=None):
    # Камера закреплена: правая кнопка мыши вращает сами фигуры (см. SyncRotator),
    # иначе фигуры поменялись бы местами и ушли со своих кнопок.
    rig.view((0, 0, -24), 0, interactive=False)
    return MatchingGameScreen(manager, level, seed, locked, playlist)


def open_projection(level="easy", seed=None, locked=False, playlist=None):
    rig.view((0, 0, -24), 0, interactive=False)
    return ProjectionGameScreen(manager, level, seed, locked, playlist)


def open_construction(level="easy", seed=None, locked=False, playlist=None):
    # Камера свободная: правой кнопкой мыши можно обойти стройку со всех сторон.
    # x = 1.8: камера чуть правее центра, поэтому стройка видна левее правой панели
    rig.view((1.8, 0, -17), 35)
    return ConstructionGameScreen(manager, level, seed, locked, playlist)


def open_custom():
    menu_view()
    return CustomTrainingScreen(manager, prefs.get("custom_plan"),
                                lambda plan: save_preference("custom_plan", plan))


def open_custom_results(playlist):
    """Итоги «Моей тренировки». В базу пишем по одной записи на режим, чтобы
    статистика и прогресс по режимам оставались честными."""
    saved, achievements = save_and_check_achievements(playlist.merged_by_mode())
    menu_view()
    return CustomResultsScreen(manager, playlist, saved, achievements)


def open_results(session):
    saved, achievements = save_and_check_achievements([session])
    menu_view()
    return ResultsScreen(manager, session, saved, achievements)


def open_statistics():
    menu_view()
    return StatisticsScreen(manager, load_history())


def open_progress():
    menu_view()
    return ProgressScreen(manager, load_history())


manager.register("menu", open_menu)
manager.register("settings", open_settings)
manager.register("achievements", open_achievements)
manager.register("profiles", open_profiles)
manager.register("rotation", open_rotation)
manager.register("matching", open_matching)
manager.register("projection", open_projection)
manager.register("construction", open_construction)
manager.register("results", open_results)
manager.register("custom", open_custom)
manager.register("custom_results", open_custom_results)
manager.register("statistics", open_statistics)
manager.register("progress", open_progress)

manager.go("menu")
app.run()
