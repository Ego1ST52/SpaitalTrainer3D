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

    m = SceneManager()
    m.register("menu", lambda: MainMenu(m))
    m.register("progress", lambda: ProgressScreen(m, HISTORY))
    m.register("statistics", lambda: StatisticsScreen(m, HISTORY))
    m.register("rotation", lambda: RotationGameScreen(m))
    m.register("matching", lambda: MatchingGameScreen(m))
    m.register("projection", lambda: ProjectionGameScreen(m))
    m.go("menu")
    app.step()
    yield m
    m.go("menu")
    app.step()


@pytest.mark.parametrize("screen", ["progress", "statistics", "rotation", "matching", "projection"])
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
