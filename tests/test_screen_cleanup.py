"""Проверка, что экраны полностью убирают за собой объекты.

Ursina запускается без окна (offscreen). После перехода «экран -> меню»
в сцене должно остаться столько же объектов, сколько было на меню.
"""

import pytest

ursina = pytest.importorskip("ursina")


@pytest.fixture
def app(ursina_app):          # ursina_app - см. conftest.py
    return ursina_app


HISTORY = [{"id": i, "mode": "rotation", "level": "easy",
            "played_at": f"2026-11-0{i + 1}T10:00:00", "tasks_total": 10,
            "tasks_correct": 5 + i, "points": 100, "total_seconds": 60.0}
           for i in range(5)]


def count_entities():
    return len([e for e in ursina.scene.entities
                if e and not getattr(e, "eternal", False)])


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
    m.go("menu")
    app.step()
    yield m
    m.go("menu")
    app.step()


@pytest.mark.parametrize("screen", ["progress", "statistics", "rotation", "matching", "projection", "construction",
                                    "settings", "profiles"])
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
