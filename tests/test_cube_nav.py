import pytest

from logic.cube_nav import CONTENT_FACE, CubeNavigator, FACE_CONTENT, RING


def test_starts_on_rotation_mode():
    nav = CubeNavigator()
    assert nav.front_face == "front" and nav.front_content == "rotation"


def test_right_arrow_walks_the_ring_in_order():
    nav = CubeNavigator()
    seen = []
    for _ in range(4):
        assert nav.move("right")
        seen.append(nav.front_content)
    assert seen == ["matching", "projection", "construction", "rotation"]


def test_left_is_reverse_of_right():
    nav = CubeNavigator()
    nav.move("left")
    assert nav.front_content == "construction"
    nav.move("right")
    assert nav.front_content == "rotation"


def test_top_and_bottom():
    nav = CubeNavigator(yaw=2)
    assert nav.move("up") and nav.front_content == "workshop"
    assert not nav.move("up")                     # выше некуда
    assert not nav.move("left")                   # на верхней грани пояс не крутим
    assert nav.move("down") and nav.front_content == "projection"   # вернулись туда же
    assert nav.move("down") and nav.front_content == "hub"
    assert not nav.move("down")


def test_every_face_has_unique_content():
    assert len(set(FACE_CONTENT.values())) == 6
    assert set(CONTENT_FACE) == {"rotation", "matching", "projection", "construction",
                                 "workshop", "hub"}


@pytest.mark.parametrize("start", [(0, 0), (3, 0), (1, 1), (2, -1)])
@pytest.mark.parametrize("target", RING + ["top", "bottom"])
def test_path_to_reaches_any_face(start, target):
    nav = CubeNavigator(*start)
    path = nav.path_to(target)
    for step in path:
        assert nav.move(step)
    assert nav.front_face == target
    assert len(path) <= 3                          # всегда коротко


def test_path_to_neighbour_is_one_step():
    assert CubeNavigator(yaw=0).path_to("left") == ["left"]
    assert CubeNavigator(yaw=0).path_to("right") == ["right"]
    assert CubeNavigator(yaw=0).path_to("front") == []
