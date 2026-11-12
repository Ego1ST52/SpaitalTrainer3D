import sqlite3
import webbrowser

from ursina import *
from ursina.lights import DirectionalLight, AmbientLight
from ursina.shaders import lit_with_shadows_shader

from core import settings
from core.fonts import setup_input_font
from core.preferences import prefs
from core import stereo
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
from interface.nets_interface import NetsGameScreen
from interface.sections_interface import SectionsGameScreen
from interface.count_interface import CAMERA_VIEW as COUNT_CAMERA, CountGameScreen
from interface.memory_interface import MemoryGameScreen
from interface.shadow_interface import ShadowGameScreen
from interface.reverse_interface import ReverseGameScreen
from interface.build_modes import SymmetryGameScreen, ThreeViewsGameScreen
from interface.results_screen import ResultsScreen
from interface.statistics_screen import StatisticsScreen
from interface.progress_screen import ProgressScreen
from interface.settings_screen import SettingsScreen
from interface.profiles_screen import ProfilesScreen
from interface.custom_screen import CustomTrainingScreen
from interface.custom_results_screen import CustomResultsScreen
from interface.achievements_screen import AchievementsScreen
from interface.analysis_screen import AnalysisScreen
from logic.achievements import newly_unlocked, unlocked_skins
from logic.report import build_rows, report_path, write_csv
from logic.html_report import build_html, write_html
from logic.assessment import STAGE_NAMES, summarize_test
from interface.records_screen import RecordsScreen
from interface.research_screen import ResearchScreen
from interface.demo import DemoDirector, DemoStartScreen
from interface.changed_interface import ChangedGameScreen
from interface.observer_interface import ObserverGameScreen
from interface.blitz_interface import BlitzGameScreen
from interface.class_screen import ClassTaskScreen
from interface.course_screen import CourseScreen
from logic.class_tasks import add_assignment, limits, make_assignment, results_for
from logic.course import LESSONS, advance, lesson_passed
from logic.playlist import MODE_ORDER, Playlist
from logic.review import due_items, review_plan, update_review
from interface import game_common
from interface.duel_screens import DuelPassScreen, DuelResultsScreen, DuelSetupScreen

# Стерео-3D (красно-синие очки) включается только до создания окна
STEREO = stereo.wanted(settings.DB_PATH)
if STEREO:
    stereo.enable_before_window()

app = Ursina(title=settings.WINDOW_TITLE, borderless=False)
if STEREO:
    stereo.configure(camera)
window.color = color.hex(settings.BACKGROUND)
# Служебные счётчики Ursina (кадры, объекты) показываем только для отладки
window.editor_ui.enabled = settings.SHOW_FPS

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

def load_class_tasks():
    """Задания для класса (общие для всех игроков на этом компьютере)."""
    if db is None:
        return []
    try:
        return db.get_state("class_tasks", []) or []
    except sqlite3.Error:
        return []


game_common.class_limits = limits(load_class_tasks())

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
def write_preference(key, value):
    """Записать настройку текущего игрока в базу (prefs.save вызывает это сам)."""
    if db is not None and player["id"] is not None:
        try:
            db.set_setting(player["id"], key, value)
        except sqlite3.Error as error:
            print("Не удалось сохранить настройку:", error)


prefs.saver = write_preference


def save_preference(key, value):
    """Изменить настройку текущего игрока и сохранить её в базе."""
    prefs.save(key, value)


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


def rename_user(user_id, name):
    """Переименовать игрока. Возвращает текст ошибки или None."""
    try:
        db.rename_user(user_id, name)
        if user_id == player["id"]:
            activate_user(user_id)          # обновить имя в меню
    except ValueError as error:
        return str(error)
    except sqlite3.Error:
        return "Не удалось сохранить новое имя."
    return None


def delete_user(user_id):
    """Удалить игрока. Если удалили текущего - выбрать первого из оставшихся."""
    try:
        db.delete_user(user_id)
        if user_id == player["id"]:
            activate_user(db.list_users()[0]["id"])
    except ValueError as error:
        return str(error)
    except sqlite3.Error:
        return "Не удалось удалить игрока."
    return None


def make_report():
    """Отчёт для учителя по всем игрокам. Возвращает сообщение для экрана."""
    if db is None:
        return "База данных недоступна - отчёт не собрать."
    try:
        players = [(u["name"], db.get_history(u["id"]), db.get_task_log(u["id"]),
                    db.get_settings(u["id"]).get("assessment"))
                   for u in db.list_users()]
        path = write_csv(build_rows([p[:3] for p in players]), report_path())
        page = write_html(build_html(players))
    except (sqlite3.Error, OSError) as error:
        return f"Не удалось сохранить отчёт: {error}"
    try:
        webbrowser.open(page.as_uri())          # страницу с графиками - сразу в браузер
    except Exception as error:                  # браузера может и не быть
        print("Не удалось открыть браузер:", error)
    return f"Сохранено: Документы › SpatialTrainer3D › {path.stem} (.csv и .html)"


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
    game_common.active_duel = None      # вышли в меню - дуэль (если была) закончилась
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
    return ProfilesScreen(manager, list_users(), player["id"], select_user, create_user,
                          rename_user, delete_user, make_report)


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


def open_nets(level="easy", seed=None, locked=False, playlist=None):
    # Камера закреплена и смотрит на развёртку сверху-спереди, как на лист на столе
    rig.view((0, 0, -13), 48, interactive=False)
    return NetsGameScreen(manager, level, seed, locked, playlist)


def open_sections(level="easy", seed=None, locked=False, playlist=None):
    # Камеру можно вращать; x = 1.9 - куб левее, правая часть экрана для вариантов
    rig.view((2.6, 0, -16), 24)
    return SectionsGameScreen(manager, level, seed, locked, playlist)


def open_count(level="easy", seed=None, locked=False, playlist=None):
    # Камера закреплена: если обойти башню, считать было бы слишком просто
    position, pitch = COUNT_CAMERA
    rig.view(position, pitch, interactive=False)
    return CountGameScreen(manager, level, seed, locked, playlist)


def open_memory(level="easy", seed=None, locked=False, playlist=None):
    rig.view((1.8, 0, -17), 35)          # как в «Конструировании»
    return MemoryGameScreen(manager, level, seed, locked, playlist)


def open_shadow(level="easy", seed=None, locked=False, playlist=None):
    # Камера закреплена: лампа и стена стоят на своих местах
    rig.view((3.2, 0, -19), 28, interactive=False)
    return ShadowGameScreen(manager, level, seed, locked, playlist)


def open_reverse(level="easy", seed=None, locked=False, playlist=None):
    # Камера закреплена: оба куба должны быть видны одинаково
    rig.view((0, 0, -14), 18, interactive=False)
    return ReverseGameScreen(manager, level, seed, locked, playlist)


def open_symmetry(level="easy", seed=None, locked=False, playlist=None):
    rig.view((1.8, 0, -17), 35)          # как в «Конструировании»
    return SymmetryGameScreen(manager, level, seed, locked, playlist)


def open_views(level="easy", seed=None, locked=False, playlist=None):
    rig.view((1.8, 0, -17), 35)
    return ThreeViewsGameScreen(manager, level, seed, locked, playlist)


def open_changed(level="easy", seed=None, locked=False, playlist=None):
    # Камеру можно вращать: фигуру разрешено осмотреть со всех сторон
    rig.view((2.2, 0, -14), 20)
    return ChangedGameScreen(manager, level, seed, locked, playlist)


def open_observer(level="easy", seed=None, locked=False, playlist=None):
    # Камера закреплена: «вы» - это камера, человечек стоит у другого края
    rig.view((1.7, 0, -19.5), 30, interactive=False)
    return ObserverGameScreen(manager, level, seed, locked, playlist)


def open_blitz(level="easy", seed=None, locked=False, playlist=None):
    rig.view((0, 0, -14), 18, interactive=False)
    return BlitzGameScreen(manager, level, seed, locked, playlist)


# ---------- повторение, продолжение, курс, класс ----------
def record_review(sessions):
    """Задания с ошибками - в список «Повторить ошибки»; верные ответы при
    повторении продвигают задания по коробкам (logic/review.py)."""
    items = prefs.get("review")
    for session in sessions:
        source = getattr(session, "source", None)
        if source is None or not session.results:
            continue
        outcomes = list(zip(source.keys, [r.correct for r in session.results]))
        items = update_review(items, session.mode, outcomes,
                              reviewing=bool(getattr(session, "review_items", None)))
    save_preference("review", items)


def open_review():
    """Тренировка из заданий, которые пора повторить."""
    steps, groups = review_plan(due_items(prefs.get("review")), MODE_ORDER)
    if not steps:
        return open_menu()
    playlist = Playlist(steps, "medium", adaptive=False)
    playlist.review = groups
    return mode_openers()[steps[0][0]](playlist=playlist)


def open_resume():
    """Продолжить недоигранную тренировку с того же задания."""
    data = prefs.get("resume")
    if not data or data["mode"] not in mode_openers():
        return open_menu()
    game_common.pending_resume = data
    return mode_openers()[data["mode"]](data["level"], data["seed"], data.get("locked", False))


def open_course(message=""):
    menu_view()
    return CourseScreen(manager, prefs.get("course"), message)


def open_lesson_results(playlist):
    save_and_check_achievements(playlist.merged_by_mode())
    record_review(playlist.sessions)
    lesson = LESSONS[playlist.lesson]
    save_preference("course", advance(prefs.get("course"), playlist))
    if lesson_passed(playlist):
        message = f"Урок «{lesson.title}» пройден: точность {playlist.accuracy:.0f}%"
    else:
        message = (f"Урок «{lesson.title}» не пройден: {playlist.accuracy:.0f}% "
                   f"(нужно {lesson.goal}%). Попробуйте ещё раз")
    return open_course(message)


def create_class_task(mode, level, minutes):
    """Новое задание для класса - в базу; возвращает список заданий."""
    tasks = add_assignment(load_class_tasks(), make_assignment(mode, level, minutes))
    if db is not None:
        try:
            db.set_state("class_tasks", tasks)
        except sqlite3.Error as error:
            print("Не удалось сохранить задание:", error)
    game_common.class_limits = limits(tasks)
    return tasks


def all_players():
    """[(имя, история)] всех игроков на этом компьютере."""
    if db is None:
        return []
    try:
        return [(u["name"], db.get_history(u["id"])) for u in db.list_users()]
    except sqlite3.Error:
        return []


def export_class_task(code):
    rows = results_for(code, all_players())
    if not rows:
        return "По этому коду ещё никто не решал."
    try:
        path = write_csv(rows, report_path().with_name(f"класс_{code}.csv"))
    except OSError as error:
        return f"Не удалось сохранить: {error}"
    return f"Сохранено: Документы › SpatialTrainer3D › {path.name}"


def open_class_task():
    menu_view()
    return ClassTaskScreen(manager, load_class_tasks(), all_players(), create_class_task,
                           export_class_task)


# ---------- игра вдвоём ----------
def mode_openers():
    """Режим -> функция, открывающая его экран (нужно дуэли)."""
    return {"rotation": open_rotation, "matching": open_matching,
            "projection": open_projection, "construction": open_construction,
            "nets": open_nets, "sections": open_sections, "count": open_count,
            "memory": open_memory, "shadow": open_shadow, "reverse": open_reverse,
            "symmetry": open_symmetry, "views": open_views, "changed": open_changed,
            "observer": open_observer, "blitz": open_blitz}


def open_duel_setup():
    menu_view()
    return DuelSetupScreen(manager, list_users(), player["id"])


def open_duel_start(duel):
    """Начать дуэль: ходит первый игрок, задания - по общему коду."""
    game_common.active_duel = duel
    select_user(duel.current_player["id"])
    return open_duel_continue(duel)


def open_duel_continue(duel):
    return mode_openers()[duel.mode](duel.level, duel.seed, True)


def open_duel_turn(session):
    """Ход окончен: сохранить результат игрока и передать ход (или итоги)."""
    duel = session.duel
    save_and_check_achievements([session])
    record_review([session])
    duel.finish_turn(session)
    menu_view()
    if not duel.is_done:
        select_user(duel.current_player["id"])
        return DuelPassScreen(manager, duel)
    game_common.active_duel = None
    select_user(duel.players[0]["id"])            # после дуэли - снова первый игрок
    return DuelResultsScreen(manager, duel)


def open_custom():
    menu_view()
    return CustomTrainingScreen(manager, prefs.get("custom_plan"),
                                lambda plan: save_preference("custom_plan", plan))


def open_custom_results(playlist):
    """Итоги «Моей тренировки». В базу пишем по одной записи на режим, чтобы
    статистика и прогресс по режимам оставались честными."""
    saved, achievements = save_and_check_achievements(playlist.merged_by_mode())
    record_review(playlist.sessions)
    menu_view()
    return CustomResultsScreen(manager, playlist, saved, achievements)


def open_results(session):
    saved, achievements = save_and_check_achievements([session])
    record_review([session])
    menu_view()
    return ResultsScreen(manager, session, saved, achievements)


def load_task_log():
    """Журнал заданий текущего игрока или None, если база недоступна."""
    if db is None or player["id"] is None:
        return None
    try:
        return db.get_task_log(player["id"])
    except sqlite3.Error as error:
        print("Не удалось прочитать журнал заданий:", error)
        return None


def open_records():
    menu_view()
    players = None
    if db is not None:
        try:
            players = [(u["name"], db.get_history(u["id"])) for u in db.list_users()]
        except sqlite3.Error as error:
            print("Не удалось прочитать рекорды:", error)
    return RecordsScreen(manager, players, player["name"])


def open_research(message=""):
    menu_view()
    return ResearchScreen(manager, prefs.get("assessment"), load_task_log(), message)


def open_test_results(playlist):
    """Тест пройден: задания - в базу (как обычные тренировки), итоги - в
    настройки игрока, чтобы потом сравнить входной и итоговый тест."""
    save_and_check_achievements(playlist.merged_by_mode())
    record_review(playlist.sessions)
    summary = summarize_test(playlist)
    results = prefs.get("assessment")
    results[playlist.stage] = summary
    save_preference("assessment", results)
    return open_research(f"{STAGE_NAMES[playlist.stage]} сохранён: точность "
                         f"{summary['accuracy']:.0f}%, среднее время {summary['seconds']:.1f} с")


def open_demo():
    """Демо-режим: заставка, дальше режимы открывает DemoDirector сам."""
    menu_view()
    DemoDirector(manager)
    return DemoStartScreen(manager)


def open_analysis():
    menu_view()
    return AnalysisScreen(manager, load_task_log())


def open_statistics():
    menu_view()
    return StatisticsScreen(manager, load_history())


def open_progress():
    menu_view()
    return ProgressScreen(manager, load_history())


manager.register("menu", open_menu)
manager.register("settings", open_settings)
manager.register("achievements", open_achievements)
manager.register("analysis", open_analysis)
manager.register("profiles", open_profiles)
manager.register("rotation", open_rotation)
manager.register("matching", open_matching)
manager.register("projection", open_projection)
manager.register("construction", open_construction)
manager.register("nets", open_nets)
manager.register("sections", open_sections)
manager.register("count", open_count)
manager.register("memory", open_memory)
manager.register("shadow", open_shadow)
manager.register("reverse", open_reverse)
manager.register("symmetry", open_symmetry)
manager.register("views", open_views)
manager.register("results", open_results)
manager.register("custom", open_custom)
manager.register("duel_setup", open_duel_setup)
manager.register("duel_start", open_duel_start)
manager.register("duel_continue", open_duel_continue)
manager.register("duel_turn", open_duel_turn)
manager.register("custom_results", open_custom_results)
manager.register("statistics", open_statistics)
manager.register("records", open_records)
manager.register("research", open_research)
manager.register("test_results", open_test_results)
manager.register("demo", open_demo)
manager.register("changed", open_changed)
manager.register("observer", open_observer)
manager.register("blitz", open_blitz)
manager.register("review", open_review)
manager.register("resume", open_resume)
manager.register("course", open_course)
manager.register("lesson_results", open_lesson_results)
manager.register("class_task", open_class_task)
manager.register("progress", open_progress)

manager.go("menu")
app.run()
