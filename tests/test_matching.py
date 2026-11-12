import random
import pytest

from logic.rotations import all_orientations
from logic.shapes import (normalize, rotate_shape, canonical, mirror,
                          same_up_to_rotation, is_connected,
                          random_shape, modify_shape)
from logic.matching_tasks import MatchingTaskGenerator, MATCHING_LEVELS
from logic.answer_checker import check_answer

SCREW = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1))      # винтовая (несимметричная)
L_FLAT = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0))     # плоская Г-образная
LINE = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0))


@pytest.mark.parametrize("shape", [SCREW, L_FLAT, LINE])
def test_canonical_is_same_for_all_rotations(shape):
    for m in all_orientations():
        assert canonical(rotate_shape(shape, m)) == canonical(shape)


def test_mirror_of_screw_is_different():
    assert not same_up_to_rotation(SCREW, mirror(SCREW))


def test_flat_L_equals_its_mirror():
    assert same_up_to_rotation(L_FLAT, mirror(L_FLAT))


def test_different_shapes_are_different():
    assert not same_up_to_rotation(LINE, L_FLAT)


def test_normalize_moves_to_origin():
    assert normalize([(5, 5, 5), (6, 5, 5)]) == ((0, 0, 0), (1, 0, 0))


def test_is_connected():
    assert is_connected(LINE)
    assert not is_connected([(0, 0, 0), (2, 0, 0)])


def test_random_shape_is_connected_with_right_count():
    rng = random.Random(1)
    for count in (4, 6, 8):
        for _ in range(50):
            shape = random_shape(rng, count)
            assert len(shape) == count and is_connected(shape)


def test_modify_shape():
    rng = random.Random(2)
    for _ in range(50):
        shape = random_shape(rng, 6)
        changed = modify_shape(rng, shape)
        assert changed is not None
        assert len(changed) == 6 and is_connected(changed)
        assert not same_up_to_rotation(shape, changed)


@pytest.mark.parametrize("level", list(MATCHING_LEVELS))
def test_generated_task_is_correct(level):
    gen = MatchingTaskGenerator(seed=3)
    config = MATCHING_LEVELS[level]
    for _ in range(100):
        task = gen.generate(level)
        assert len(task.options) == config["options"]
        # правильный вариант совпадает с образцом после поворота
        assert same_up_to_rotation(task.reference, task.correct_option)
        # все остальные - нет
        for index, option in enumerate(task.options):
            if index != task.correct_index:
                assert not same_up_to_rotation(task.reference, option)
        # все варианты разные между собой и связные
        keys = [canonical(o) for o in task.options]
        assert len(set(keys)) == len(keys)
        assert all(is_connected(o) for o in task.options)


@pytest.mark.parametrize("level", list(MATCHING_LEVELS))
def test_no_same_reference_twice_in_a_row(level):
    gen = MatchingTaskGenerator(seed=4)
    previous = canonical(gen.generate(level).reference)
    for _ in range(100):
        current = canonical(gen.generate(level).reference)
        assert current != previous
        previous = current


def test_check_answer_works_with_matching_tasks():
    task = MatchingTaskGenerator(seed=5).generate("easy")
    assert check_answer(task, task.correct_index) is True


def test_unknown_level_raises():
    with pytest.raises(ValueError):
        MatchingTaskGenerator().generate("impossible")

def test_solution_turns_correct_option_back_into_reference():
    from logic.rotations import IDENTITY, apply_sequence
    from logic.shapes import normalize, rotate_shape
    gen = MatchingTaskGenerator(seed=11)
    for level in ("easy", "medium", "hard"):
        for _ in range(30):
            task = gen.generate(level)
            back = apply_sequence(IDENTITY, task.solution_moves)
            assert rotate_shape(task.correct_option, back) == normalize(task.reference)


def test_captions_and_explanations_follow_kinds():
    gen = MatchingTaskGenerator(seed=12)
    task = gen.generate("hard")
    assert task.option_caption(task.correct_index) == "та же фигура"
    assert task.explain(task.correct_index) is None
    for i, kind in enumerate(task.kinds):
        if kind == "mirror":
            assert task.option_caption(i) == "зеркальная копия"
            assert "зеркальная" in task.explain(i)
        elif kind == "changed":
            assert "другая фигура" in task.explain(i)


def test_solution_is_shortest_and_empty_when_already_aligned():
    from logic.matching_tasks import MatchingTask
    from logic.rotations import rotate
    square = ((0, 0, 0), (0, 1, 0), (1, 0, 0), (1, 1, 0))          # квадрат 2x2
    turned = rotate((((1, 0, 0), (0, 1, 0), (0, 0, 1))), "z", 90)
    task = MatchingTask("easy", square, (rotate_shape(square, turned),), 0, ("correct",))
    assert task.solution_moves == []          # квадрат после поворота на 90° - тот же
