"""Проверка, что экраны полностью убирают за собой объекты.

Ursina запускается без окна (offscreen). После перехода «экран -> меню»
в сцене должно остаться столько же объектов, сколько было на меню.
"""

import pytest

ursina = pytest.importorskip("ursina")
from ursina import Text, scene  # noqa: E402


@pytest.fixture
def app(ursina_app):          # ursina_app - см. conftest.py
    return ursina_app


HISTORY = [{"id": i, "mode": "rotation", "level": "easy",
            "played_at": f"2026-11-0{i + 1}T10:00:00", "tasks_total": 10,
            "tasks_correct": 5 + i, "points": 100, "total_seconds": 60.0}
           for i in range(5)]


def _finished_playlist():
    """Пройденная «Моя тренировка» из двух режимов (для экрана итогов)."""
    from logic.playlist import Playlist
    from logic.session import TrainingSession
    playlist = Playlist([("rotation", 2), ("projection", 1)], "easy", adaptive=True)
    for mode, answers in (("rotation", (True, False)), ("projection", (True,))):
        session = TrainingSession(mode, "easy", len(answers), adaptive=playlist.adaptive)
        for answer in answers:
            session.record(answer, 4)
        playlist.finish_step(session)
    return playlist


def count_entities():
    return len([e for e in ursina.scene.entities
                if e and not getattr(e, "eternal", False)])


def _duel(turns):
    """Дуэль Ани и Бориса, в которой сыграно turns ходов."""
    from logic.duel import Duel
    from logic.session import TrainingSession

    duel = Duel([{"id": 1, "name": "Аня", "color": "#22d3ee"},
                 {"id": 2, "name": "Борис", "color": "#a78bfa"}], "rotation", "easy", seed=5)
    for k in range(turns):
        session = TrainingSession("rotation", "easy", 3, code=duel.code, locked=True)
        for answer in (True, k == 0, False):
            session.record(answer, 4)
        duel.finish_turn(session)
    return duel


@pytest.fixture
def manager(app):
    from core.scene_manager import SceneManager
    from interface.main_menu import MainMenu
    from interface.progress_screen import ProgressScreen
    from interface.statistics_screen import StatisticsScreen
    from interface.game_interface import RotationGameScreen
    from interface.matching_interface import MatchingGameScreen
    from interface.projection_interface import ProjectionGameScreen
    from interface.construction_interface import ConstructionGameScreen
    from interface.settings_screen import SettingsScreen
    from interface.profiles_screen import ProfilesScreen
    from interface.custom_screen import CustomTrainingScreen
    from interface.custom_results_screen import CustomResultsScreen
    from core.preferences import DEFAULTS
    from interface.achievements_screen import AchievementsScreen
    from interface.nets_interface import NetsGameScreen
    from interface.sections_interface import SectionsGameScreen
    from interface.count_interface import CountGameScreen
    from interface.memory_interface import MemoryGameScreen
    from interface.shadow_interface import ShadowGameScreen
    from interface.analysis_screen import AnalysisScreen
    log = ([{"mode": "rotation", "level": "easy", "correct": True, "seconds": 3,
             "played_at": "2026-11-12T10:00:00", "tags": ["axis:x"]}] * 10
           + [{"mode": "rotation", "level": "easy", "correct": False, "seconds": 3,
               "played_at": "2026-11-12T10:00:00", "tags": ["axis:z"]}] * 6)

    m = SceneManager()
    m.register("menu", lambda: MainMenu(m))
    m.register("progress", lambda: ProgressScreen(m, HISTORY))
    m.register("statistics", lambda: StatisticsScreen(m, HISTORY))
    m.register("rotation", lambda: RotationGameScreen(m))
    m.register("matching", lambda: MatchingGameScreen(m))
    m.register("projection", lambda: ProjectionGameScreen(m))
    m.register("construction", lambda: ConstructionGameScreen(m))
    m.register("settings", lambda: SettingsScreen(m, "Тест", lambda key, value: None))
    users = [{"id": 1, "name": "Аня", "color": "#22d3ee", "sessions": 3},
             {"id": 2, "name": "Борис", "color": "#a78bfa", "sessions": 0}]
    m.register("profiles", lambda: ProfilesScreen(m, users, 1, lambda uid: None,
                                                  lambda name: None))
    m.register("custom", lambda: CustomTrainingScreen(m, DEFAULTS["custom_plan"],
                                                      lambda plan: None))
    m.register("custom_results", lambda: CustomResultsScreen(m, _finished_playlist()))
    m.register("achievements", lambda: AchievementsScreen(m, HISTORY, 20, lambda goal: None))
    m.register("nets", lambda: NetsGameScreen(m, "hard"))
    m.register("sections", lambda: SectionsGameScreen(m, "hard"))
    m.register("count", lambda: CountGameScreen(m, "hard"))
    m.register("memory", lambda: MemoryGameScreen(m, "easy"))
    m.register("shadow", lambda: ShadowGameScreen(m, "hard"))
    m.register("analysis", lambda: AnalysisScreen(m, log))
    from interface.duel_screens import DuelPassScreen, DuelResultsScreen, DuelSetupScreen
    m.register("duel_setup", lambda: DuelSetupScreen(m, users, 1))
    m.register("duel_pass", lambda: DuelPassScreen(m, _duel(turns=1)))
    m.register("duel_results", lambda: DuelResultsScreen(m, _duel(turns=2)))
    m.go("menu")
    app.step()
    yield m
    m.go("menu")
    app.step()


@pytest.mark.parametrize("screen", ["progress", "statistics", "rotation", "matching", "projection", "construction",
                                    "settings", "profiles", "custom", "custom_results",
                                    "achievements", "nets", "sections", "count",
                                    "memory", "shadow", "analysis", "duel_setup",
                                    "duel_pass", "duel_results"])
def test_screen_leaves_nothing_behind(app, manager, screen):
    before = count_entities()
    manager.go(screen)
    app.step()
    manager.go("menu")
    app.step()
    assert count_entities() == before


def test_progress_filters_do_not_leak(app, manager):
    before = count_entities()
    manager.go("progress")
    app.step()
    screen = manager._current
    for _ in range(4):           # перебираем фильтры: график перерисовывается
        screen.next_mode()
        screen.next_level()
        app.step()
    manager.go("menu")
    app.step()
    assert count_entities() == before


def test_matching_shape_can_be_clicked(app, manager):
    """Клик по самой 3D-фигуре засчитывается как выбор этого варианта."""
    from ursina import mouse

    manager.go("matching")
    app.step()
    screen = manager._current
    target = 1
    cube = screen.option_views[target].cubes[0]
    assert cube.collider is not None          # без коллайдера мышь его не «увидит»
    # Окно без экрана не умеет двигать курсор, поэтому говорим напрямую,
    # какой кубик под курсором (так делает Ursina каждый кадр).
    mouse.hovered_entity = cube
    assert screen._option_under_mouse() == target
    screen.input("left mouse down")
    assert screen.answered
    assert screen.session.results[-1].correct == (target == screen.task.correct_index)


def _point_mouse_at(entity, world_point=(0, 0, 0), world_normal=(0, 1, 0)):
    """Окно без экрана не двигает курсор, поэтому сами говорим, во что
    «попала» мышь и в какую точку/грань (так Ursina делает каждый кадр)."""
    from types import SimpleNamespace
    from ursina import mouse
    mouse.hovered_entity = entity
    mouse.collision = SimpleNamespace(world_point=world_point, world_normal=world_normal,
                                      point=world_point, normal=world_normal)


def test_construction_place_stack_remove_and_check(app, manager):
    from ursina import held_keys

    manager.go("construction")
    app.step()
    screen = manager._current

    # Клик по полу ставит кубик в ближайшую клетку
    _point_mouse_at(screen.ground, world_point=(1.2, -0.5, -0.8))
    screen.input("left mouse down")
    assert screen.build.cells == {(1, 0, -1)}

    # Клик по верхней грани кубика ставит новый кубик на него
    block = screen.blocks[(1, 0, -1)]
    _point_mouse_at(block, world_normal=(0, 1, 0))
    screen.input("left mouse down")
    assert screen.build.cells == {(1, 0, -1), (1, 1, -1)}

    # Shift + клик убирает кубик под курсором
    held_keys["shift"] = 1
    try:
        _point_mouse_at(screen.blocks[(1, 1, -1)])
        screen.input("left mouse down")
    finally:
        held_keys["shift"] = 0
    assert screen.build.cells == {(1, 0, -1)}
    assert set(screen.blocks) == {(1, 0, -1)}       # 3D-кубики совпадают с постройкой

    # Ctrl+Z возвращает убранный кубик
    held_keys["control"] = 1
    try:
        screen.input("z")
    finally:
        held_keys["control"] = 0
    assert set(screen.blocks) == {(1, 0, -1), (1, 1, -1)}

    # Собираем ровно образец (сдвинутый) и проверяем
    screen.clear()
    # Ставим как человек: кубик можно поставить, только если он на полу
    # или касается уже поставленного, поэтому повторяем проходы
    remaining = [(x - 2, y, z - 2) for x, y, z in screen.task.target]
    while remaining:
        placed = [cell for cell in remaining if screen.build.add(cell)]
        assert placed, "образец невозможно собрать"
        remaining = [cell for cell in remaining if cell not in placed]
    screen._sync_blocks()
    screen.check()
    assert screen.answered
    assert screen.session.results[-1].correct


def test_code_dialog_starts_locked_training(app, manager):
    """Верный код запускает нужный режим с нужным зерном, неверный - ошибка."""
    menu = manager._current
    started = []
    menu.navigate = lambda name, **kwargs: started.append((name, kwargs))

    menu.open_code_dialog()
    menu.dialog.field.text = "12"
    menu.dialog.submit()
    assert "6 цифр" in menu.dialog.error.text and not started

    menu.dialog.field.text = "31-4821"
    menu.dialog.submit()
    assert started == [("projection", {"level": "easy", "seed": 4821, "locked": True})]
    assert menu.dialog is None                     # окно закрылось


def test_locked_training_uses_code_and_fixed_length(app, manager):
    from interface.matching_interface import MatchingGameScreen
    from logic.matching_tasks import MatchingTaskGenerator

    screen = MatchingGameScreen(manager, "medium", seed=4821, locked=True)
    try:
        assert screen.session.code == "22-4821"
        assert screen.session.length == 10
        expected = MatchingTaskGenerator(seed=4821).generate("medium")
        assert screen.task == expected                 # те же задания, что у друга
        screen.input("3")                              # уровень сменить нельзя
        assert screen.session.level == "medium" and screen.session.code == "22-4821"
    finally:
        screen.close()


def test_skin_setting_changes_rotation_answers(app, manager):
    from core.preferences import prefs
    from logic.cube_skins import face_names

    prefs.set("cube_skin", "dice")
    try:
        manager.go("rotation")
        app.step()
        screen = manager._current
        assert set(screen.task.options) <= set(face_names("dice").values())
    finally:
        prefs.load({})
        manager.go("menu")
        app.step()


def test_custom_training_flows_through_modes(app, manager):
    """«Моя тренировка»: этап вращения -> этап проекций -> общие итоги.
    Адаптивный уровень общий: 3 верных ответа в разных режимах поднимают его."""
    from interface.game_interface import RotationGameScreen
    from interface.projection_interface import ProjectionGameScreen
    from logic.playlist import Playlist

    playlist = Playlist([("rotation", 2), ("projection", 1)], "easy", adaptive=True)
    calls = []

    screen = RotationGameScreen(manager, playlist=playlist)
    screen.navigate = lambda name, **kwargs: calls.append((name, kwargs))
    try:
        assert screen.session.length == 2 and screen.session.locked
        screen.input("3")                                   # уровень вручную не меняется
        assert screen.session.level == "easy"
        for _ in range(2):
            screen.choose(screen.task.correct_index)
            assert screen.next_button.text in ("Дальше", "Следующий этап")
            screen.next_task()
    finally:
        screen.close()
    assert calls == [("projection", {"playlist": playlist})]
    assert playlist.index == 1

    calls.clear()
    screen = ProjectionGameScreen(manager, playlist=playlist)
    screen.navigate = lambda name, **kwargs: calls.append((name, kwargs))
    try:
        screen.choose(screen.task.correct_index)
        assert screen.next_button.text == "Результаты"
        screen.next_task()
    finally:
        screen.close()
    assert calls == [("custom_results", {"playlist": playlist})]
    assert playlist.is_done and playlist.correct == 3
    assert playlist.adaptive.level == "medium"              # 3 верных подряд - выше


def test_custom_builder_requires_a_mode(app, manager):
    from interface.custom_screen import CustomTrainingScreen

    saved, calls = [], []
    plan = {"modes": ["rotation"], "level": "easy", "per_mode": 3, "order": "blocks",
            "adaptive": False}
    screen = CustomTrainingScreen(manager, plan, saved.append)
    screen.navigate = lambda name, **kwargs: calls.append((name, kwargs))
    try:
        screen.toggle("rotation")                           # сняли единственный режим
        screen.start()
        assert "хотя бы один" in screen.error.text and not calls
        screen.toggle("matching")
        screen.change("per_mode", 5)
        screen.start()
        assert saved[-1]["modes"] == ["matching"] and saved[-1]["per_mode"] == 5
        name, kwargs = calls[-1]
        assert name == "matching" and kwargs["playlist"].steps == [("matching", 5)]
    finally:
        screen.close()


def _fresh_menu(manager, app):
    from interface.main_menu import MainMenu
    MainMenu.remembered_nav, MainMenu.remembered_turns = (0, 0), 0
    manager.go("menu")
    app.step()
    menu = manager._current
    calls = []
    menu.navigate = lambda name, **kwargs: calls.append((name, kwargs))
    return menu, calls


def test_cube_menu_turns_and_opens_mode(app, manager):
    import time
    menu, calls = _fresh_menu(manager, app)
    assert menu.nav.front_content == "rotation"
    menu.input("right arrow")
    assert menu.nav.front_content == "matching" and menu.cube.yaw_turns == 1
    menu.input("enter")
    deadline = time.time() + 2
    while not calls and time.time() < deadline:      # ждём «влёт» в грань
        app.step()
    assert calls == [("matching", {"level": menu.level})]


def test_clicking_side_face_turns_cube(app, manager):
    menu, calls = _fresh_menu(manager, app)
    side = [e for e in menu.cube.contents["left"].children if e.collider][0]
    menu._click(side)                                 # клик по краю левой грани
    assert menu.nav.front_face == "left" and menu.nav.front_content == "construction"
    assert not calls                                   # только повернули, не открыли


def test_cube_net_jumps_to_face(app, manager):
    menu, calls = _fresh_menu(manager, app)
    menu.go_to("bottom")
    assert menu.nav.front_content == "hub"
    menu.go_to("top")
    assert menu.nav.front_content == "workshop"


def test_hub_buttons_work_only_when_hub_is_in_front(app, manager):
    menu, calls = _fresh_menu(manager, app)
    menu._hub_action("settings")
    assert not calls                                   # спереди «Вращение» - кнопка спит
    menu.go_to("bottom")
    menu._hub_action("settings")
    assert calls == [("settings", {})]


def test_rotation_manual_turns_only_after_answer(app, manager):
    """Самому крутить куб можно после ответа (до ответа - только с подсказкой
    в настройках). Направления: «вправо» уводит переднюю грань вправо."""
    import time
    from core.preferences import prefs
    from logic.rotations import face_direction

    def settle(screen):
        deadline = time.time() + 2
        while screen.cube.busy and time.time() < deadline:
            app.step()

    manager.go("rotation")
    app.step()
    screen = manager._current
    assert not screen.manual_turn("y", -1)             # до ответа нельзя
    assert "после ответа" in screen.manual_title.text

    screen.choose(0)
    assert screen.manual_turn("y", -1)                 # «вправо» вокруг Y
    settle(screen)
    assert face_direction(screen.cube.orientation, "-Z") == "+X"
    assert screen.manual_turn("x", 1)                  # «вверх» вокруг X
    settle(screen)
    assert screen.manual_log.text.endswith("Y-  X+")
    screen.manual_reset()
    assert screen.cube.orientation == ((1, 0, 0), (0, 1, 0), (0, 0, 1))

    prefs.set("free_rotation", True)
    try:
        screen.next_task()
        assert screen.manual_turn("z", 1)              # подсказка: можно и до ответа
        settle(screen)
    finally:
        prefs.load({})
        manager.go("menu")
        app.step()


def test_leaving_during_manual_turn_does_not_crash(app, manager):
    """Ушли с экрана, пока куб ещё поворачивается - конец анимации не должен
    обращаться к уже удалённому кубу."""
    import time
    manager.go("rotation")
    app.step()
    screen = manager._current
    screen.choose(0)
    assert screen.manual_turn("x", 1)
    manager.go("menu")                                 # ушли посреди поворота
    deadline = time.time() + 1
    while time.time() < deadline:
        app.step()                                     # таймер окончания поворота сработает


def test_locked_skin_cannot_be_picked(app, manager):
    from core.preferences import prefs
    from interface.settings_screen import SettingsScreen

    saved = []
    screen = SettingsScreen(manager, "Тест", lambda key, value: saved.append((key, value)),
                            unlocked_skins={"pastel"})
    try:
        screen.pick_skin("neon")                       # «Неон» закрыт
        assert not saved and "Без ошибок" in screen.skin_hint.text
        screen.pick_skin("pastel")                     # открыт - выбирается
        assert saved == [("cube_skin", "pastel")]
    finally:
        screen.close()
        prefs.load({})


def test_results_show_new_achievements(app, manager):
    from interface.results_screen import ResultsScreen
    from logic.achievements import BY_KEY
    from logic.session import TrainingSession

    session = TrainingSession("rotation", "easy", 5)
    for _ in range(5):
        session.record(True, 3)
    screen = ResultsScreen(manager, session, True, [BY_KEY["flawless"]])
    try:
        texts = [e.text for e in scene.entities if isinstance(e, Text) and e.enabled]
        assert "Новое достижение!" in texts and "Без ошибок" in texts
        assert any("Неон" in t for t in texts)
    finally:
        screen.close()


def test_theme_recolors_new_widgets_and_resets(app):
    from core import settings
    from core.theme import apply_theme
    from interface.ui_kit import label, UIButton
    from engine.objects import dispose
    from logic.theme import build_palette

    original_accent = settings.ACCENT
    palette = apply_theme("#ff7a45")
    try:
        assert settings.ACCENT == palette["ACCENT"] != original_accent
        assert settings.MODE_COLORS["rotation"] == palette["MODE_COLORS"]["rotation"]
        button = UIButton("Тест", lambda: None, variant="primary")
        text = label("Тест", (0, 0), 1, "accent")
        assert button.color == ursina.color.hex(build_palette("#ff7a45")["SELECTED_COLOR"])
        assert text.color == ursina.color.hex(palette["ACCENT"])
        dispose(button)
        dispose(text)
    finally:
        apply_theme("")
    assert settings.ACCENT == original_accent              # «Сброс» вернул стандартную


def test_settings_theme_input(app, manager):
    from interface.settings_screen import SettingsScreen
    from logic.theme import NAMED_COLORS

    chosen = []
    screen = SettingsScreen(manager, "Тест", lambda k, v: None, on_theme=chosen.append)
    try:
        screen.theme_field.text = "радужный"
        screen.apply_typed_theme()
        assert not chosen and "Не понял цвет" in screen.theme_hint.text
        screen.theme_field.text = "мятный"
        screen.apply_typed_theme()
        assert chosen == [NAMED_COLORS["мятный"]]
    finally:
        screen.close()


def test_profiles_rename_and_delete(app, manager):
    from interface.profiles_screen import ProfilesScreen

    users = [{"id": 1, "name": "Peresvet", "color": "#22d3ee", "sessions": 3},
             {"id": 2, "name": "Борис", "color": "#a78bfa", "sessions": 0}]
    renamed, deleted, calls = [], [], []

    def fake_delete(user_id):
        deleted.append(user_id)
        return None if user_id == 2 else "Нельзя удалить единственного игрока."

    screen = ProfilesScreen(manager, users, 1, lambda uid: None, lambda name: None,
                            lambda uid, name: renamed.append((uid, name)), fake_delete)
    screen.navigate = lambda name, **kwargs: calls.append(name)
    try:
        screen.start_rename(users[0])
        assert screen.name_field.text == "Peresvet"
        assert screen.submit_button.text == "Сохранить" and screen.cancel_button.enabled
        screen.name_field.text = "Пересвет"
        screen.submit()
        assert renamed == [(1, "Пересвет")] and calls == ["profiles"]

        screen.ask_delete(users[1])
        assert screen.dialog is not None
        screen.close_dialog()                          # передумали
        assert deleted == []
        screen.ask_delete(users[1])
        screen.delete(2)
        assert deleted == [2] and calls[-1] == "profiles"

        calls.clear()
        screen.delete(1)                               # база отказала - видна ошибка
        assert "единственного" in screen.error.text and calls == []
    finally:
        screen.close()


@pytest.mark.parametrize("seed", range(6))
def test_3d_fold_matches_logic_not_mirror(app, seed):
    """3D-складывание даёт тот же кубик, что и логика, а не зеркальный:
    иначе вопрос «какой кубик получится» показывал бы неверное решение."""
    from engine.net_fold import NetFold
    from engine.objects import dispose
    from logic.nets import NetTaskGenerator
    from logic.rotations import all_orientations, face_direction

    task = NetTaskGenerator(seed=seed).generate("hard")
    net = NetFold(task.cells, task.letters)
    try:
        for hinge, axis, angle in net.hinges:          # сложить мгновенно
            setattr(hinge, axis, angle)
        directions = {(1, 0, 0): "+X", (-1, 0, 0): "-X", (0, 1, 0): "+Y",
                      (0, -1, 0): "-Y", (0, 0, 1): "+Z", (0, 0, -1): "-Z"}
        visual = {}                                    # буква -> куда смотрит её грань
        for text in [e for e in net.get_descendants() if isinstance(e, ursina.Text)]:
            up = text.parent.up                        # лицо клетки (буквы) - вверх у рамки
            visual[text.text] = directions[tuple(round(v) for v in up)]
        assert len(set(visual.values())) == 6          # все шесть граней разные
        logic = {letter: face for face, letter in task.face_letters.items()}
        assert any(all(face_direction(r, logic[l]) == visual[l] for l in logic)
                   for r in all_orientations())
    finally:
        dispose(net)


def test_count_camera_sees_top_front_left(app):
    """Логика «Сколько кубиков?» считает, что видны верх, перед и левый бок.
    Проверяем по-настоящему: какие грани кубика башни повёрнуты к камере."""
    from ursina import Entity, Vec3
    from interface.count_interface import CAMERA_VIEW, TOWER_POSITION, TOWER_YAW

    position, pitch = CAMERA_VIEW
    pivot = Entity(rotation_x=pitch)                 # так устроена камера в engine/camera.py
    cam = Entity(parent=pivot, position=position)
    tower = Entity(position=TOWER_POSITION, rotation_y=TOWER_YAW)
    try:
        faces = {"left": Vec3(-1, 0, 0), "right": Vec3(1, 0, 0), "top": Vec3(0, 1, 0),
                 "bottom": Vec3(0, -1, 0), "front": Vec3(0, 0, -1), "back": Vec3(0, 0, 1)}
        visible = set()
        for name, normal in faces.items():
            marker = Entity(parent=tower, position=normal * 0.5 + Vec3(0, 0.5, 0))
            world_normal = (marker.world_position - tower.world_position
                            - Vec3(0, 0.5, 0)).normalized()
            if world_normal.dot(cam.world_position - marker.world_position) > 0:
                visible.add(name)
            marker.removeNode()
        assert visible == {"top", "front", "left"}
    finally:
        for e in (cam, pivot, tower):
            e.removeNode()


def test_memory_hides_sample_and_blocks_building_until_hidden(app, manager):
    import time
    from interface.memory_interface import MemoryGameScreen
    from interface.shadow_interface import ShadowGameScreen
    from interface.analysis_screen import AnalysisScreen
    log = ([{"mode": "rotation", "level": "easy", "correct": True, "seconds": 3,
             "played_at": "2026-11-12T10:00:00", "tags": ["axis:x"]}] * 10
           + [{"mode": "rotation", "level": "easy", "correct": False, "seconds": 3,
               "played_at": "2026-11-12T10:00:00", "tags": ["axis:z"]}] * 6)

    screen = MemoryGameScreen(manager, "hard")
    try:
        assert screen.preview.enabled and not screen.can_build()   # смотрим и запоминаем
        screen.hide_at = time.time() - 0.01                       # время вышло
        screen.update()
        assert screen.hidden and not screen.preview.enabled and screen.can_build()
        remaining = [(x - 2, y, z - 2) for x, y, z in screen.task.target]
        while remaining:
            placed = [c for c in remaining if screen.build.add(c)]
            remaining = [c for c in remaining if c not in placed]
        screen._sync_blocks()
        screen.check()
        assert screen.session.results[-1].correct
        assert screen.preview.enabled                              # образец снова виден
        assert screen.session.mode == "memory"
    finally:
        screen.close()


def test_daily_button_starts_todays_locked_training(app, manager):
    from logic.daily import daily_task
    menu, calls = _fresh_menu(manager, app)
    menu.start_daily()
    mode, level, seed, _ = daily_task()
    assert calls == [(mode, {"level": level, "seed": seed, "locked": True})]


def test_tutorial_shows_once_and_on_help(app, manager):
    from core.preferences import prefs
    from interface.ui_kit import TopBar

    saved = []
    prefs.load({})
    prefs.saver = lambda key, value: saved.append((key, value))
    try:
        first = TopBar("sections", lambda: None)
        assert first.dialog is not None                      # первый вход - подсказка
        assert saved == [("seen_tutorials", ["sections"])]   # и отметка сохранена
        first.close_help()
        assert first.dialog is None
        ursina.destroy(first)

        second = TopBar("sections", lambda: None)
        assert second.dialog is None                         # второй раз - не мешаем
        second.show_help()                                   # кнопка «?»
        assert second.dialog is not None
        second.close_help()
        ursina.destroy(second)
    finally:
        prefs.saver = None
        prefs.load({})


def test_construction_saves_stl_after_check(app, manager, tmp_path):
    from interface.construction_interface import ConstructionGameScreen

    screen = ConstructionGameScreen(manager, "easy")
    screen.export_folder = tmp_path
    try:
        assert not screen.stl_button.enabled               # до проверки - нечего сохранять
        screen.build.add((0, 0, 0))
        screen._sync_blocks()
        screen.check()
        assert screen.stl_button.enabled
        path = screen.save_stl()
        assert path.exists() and path.read_text(encoding="ascii").startswith("solid")
        assert path.name in screen.counter.text
    finally:
        screen.close()


def test_duel_two_players_same_tasks(app, manager):
    from interface import game_common
    from interface.count_interface import CountGameScreen
    from interface.duel_screens import DuelPassScreen, DuelResultsScreen
    from logic.duel import Duel

    anya = {"id": 1, "name": "Аня", "color": "#22d3ee"}
    boris = {"id": 2, "name": "Борис", "color": "#a78bfa"}
    duel = Duel([anya, boris], "count", "easy", seed=321)
    game_common.active_duel = duel
    tasks = []
    try:
        for turn in range(2):
            calls = []
            screen = CountGameScreen(manager, duel.level, duel.seed, True)
            screen.navigate = lambda name, **kwargs: calls.append((name, kwargs))
            try:
                assert screen.session.duel is duel
                tasks.append(screen.task)
                while not calls:
                    screen.choose(screen.task.correct_index if turn == 0 else 0)
                    screen.next_task()
            finally:
                screen.close()
            name, kwargs = calls[-1]
            assert name == "duel_turn"                    # не обычные итоги, а передача хода
            duel.finish_turn(kwargs["session"])
            if turn == 0:
                DuelPassScreen(manager, duel).close()
        assert tasks[0] == tasks[1]                        # у обоих одинаковое первое задание
        assert duel.is_done and duel.winner() in (0, None)
        DuelResultsScreen(manager, duel).close()
    finally:
        game_common.active_duel = None


def test_duel_setup_needs_two_players(app, manager):
    from interface.duel_screens import DuelSetupScreen
    users = [{"id": 1, "name": "Аня", "color": "#22d3ee", "sessions": 0},
             {"id": 2, "name": "Борис", "color": "#a78bfa", "sessions": 0}]
    calls = []
    screen = DuelSetupScreen(manager, users, 1)
    screen.navigate = lambda name, **kwargs: calls.append((name, kwargs))
    try:
        screen.second.select(1)                            # оба - Аня
        screen.start()
        assert "разных" in screen.error.text and not calls
        screen.second.select(2)
        screen._mode("shadow")
        screen.start()
        duel = calls[-1][1]["duel"]
        assert duel.mode == "shadow" and [p["id"] for p in duel.players] == [1, 2]
    finally:
        screen.close()
    lonely = DuelSetupScreen(manager, users[:1], 1)
    lonely.close()


def test_stereo_setting_warns_about_restart(app, manager):
    from core.preferences import prefs
    from interface.settings_screen import STEREO_NOTE, SettingsScreen

    saved = []
    screen = SettingsScreen(manager, "Тест", lambda key, value: saved.append((key, value)))
    try:
        assert screen.stereo_note.text == ""
        screen.change("stereo", True)
        assert saved == [("stereo", True)] and screen.stereo_note.text == STEREO_NOTE
    finally:
        screen.close()
        prefs.load({})


def test_workshop_button_text_keeps_size_on_hover(app, manager):
    """Под курсором кнопка на грани куба меняет цвет, но не размер текста."""
    from interface.ui_kit import UIButton
    from ursina import Vec3

    menu, calls = _fresh_menu(manager, app)
    menu.go_to("top")
    buttons = [e for e in scene.entities
               if isinstance(e, UIButton) and getattr(e, "face_name", None) == "top"]
    assert buttons
    for button in buttons:
        before = Vec3(button.text_entity.world_scale)
        button.on_mouse_enter()
        assert (button.text_entity.world_scale - before).length() < 1e-4
        button.on_mouse_exit()
        assert (button.text_entity.world_scale - before).length() < 1e-4
