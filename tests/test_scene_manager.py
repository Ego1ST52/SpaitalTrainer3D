import pytest
from core.scene_manager import SceneManager


class FakeScreen:
    def __init__(self, name, log):
        self.name = name
        self.log = log
        log.append(f"open {name}")

    def close(self):
        self.log.append(f"close {self.name}")


def test_go_closes_previous_and_opens_new():
    log = []
    manager = SceneManager()
    manager.register("a", lambda: FakeScreen("a", log))
    manager.register("b", lambda: FakeScreen("b", log))
    manager.go("a")
    manager.go("b")
    assert log == ["open a", "close a", "open b"]


def test_unknown_screen_raises_and_keeps_current():
    log = []
    manager = SceneManager()
    manager.register("a", lambda: FakeScreen("a", log))
    manager.go("a")
    with pytest.raises(KeyError):
        manager.go("nope")
    assert log == ["open a"]  # текущий экран не закрыт


def test_kwargs_are_passed_to_factory():
    received = {}

    def factory(level):
        received["level"] = level
        return FakeScreen("g", [])

    manager = SceneManager()
    manager.register("game", factory)
    manager.go("game", level="hard")
    assert received["level"] == "hard"