import pytest
from logic.rotations import (
    IDENTITY, rotate, apply_sequence, all_orientations,
    face_direction, determinant,
)


def test_there_are_exactly_24_orientations():
    assert len(all_orientations()) == 24


def test_all_orientations_are_proper_rotations():
    # determinant 1 = поворот (-1 было бы зеркальное отражение)
    assert all(determinant(m) == 1 for m in all_orientations())


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_four_quarter_turns_return_to_start(axis):
    state = IDENTITY
    for _ in range(4):
        state = rotate(state, axis, 90)
    assert state == IDENTITY


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_turn_and_reverse_cancel(axis):
    assert rotate(rotate(IDENTITY, axis, 90), axis, -90) == IDENTITY


def test_180_equals_two_90():
    assert rotate(IDENTITY, "y", 180) == rotate(rotate(IDENTITY, "y", 90), "y", 90)


def test_order_of_rotations_matters():
    xy = apply_sequence(IDENTITY, [("x", 90), ("y", 90)])
    yx = apply_sequence(IDENTITY, [("y", 90), ("x", 90)])
    assert xy != yx


def test_known_face_positions():
    # Поворот на +90 вокруг Z переводит грань +X в +Y
    state = rotate(IDENTITY, "z", 90)
    assert face_direction(state, "+X") == "+Y"
    # а грань +Z остаётся на месте
    assert face_direction(state, "+Z") == "+Z"


def test_opposite_faces_stay_opposite():
    opposite = {"+X": "-X", "+Y": "-Y", "+Z": "-Z"}
    for m in all_orientations():
        for face, back in opposite.items():
            a, b = face_direction(m, face), face_direction(m, back)
            assert a[1] == b[1] and a[0] != b[0]


def test_rotate_does_not_change_original():
    original = IDENTITY
    rotate(original, "x", 90)
    assert original == IDENTITY


def test_invalid_input_raises():
    with pytest.raises(ValueError):
        rotate(IDENTITY, "w", 90)
    with pytest.raises(ValueError):
        rotate(IDENTITY, "x", 45)

        def test_face_at_identity():
            for name in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
                assert face_at(IDENTITY, name) == name

        def test_face_at_after_rotation():
            # После поворота на +90 вокруг Z грань +X оказывается сверху (+Y)
            state = rotate(IDENTITY, "z", 90)
            assert face_at(state, "+Y") == "+X"

        def test_face_at_is_inverse_of_face_direction():
            for m in all_orientations():
                for face in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
                    assert face_at(m, face_direction(m, face)) == face

def test_shortest_moves_reach_every_orientation():
    from logic.rotations import shortest_moves
    for target in all_orientations():
        moves = shortest_moves(target)
        assert apply_sequence(IDENTITY, moves) == target
        assert len(moves) <= 3
    assert shortest_moves(IDENTITY) == []
