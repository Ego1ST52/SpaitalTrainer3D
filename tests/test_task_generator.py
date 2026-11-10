import pytest
from logic.task_generator import (
    RotationTaskGenerator, LEVELS, top_color,
)
from logic.rotations import IDENTITY, apply_sequence
from logic.answer_checker import check_answer


@pytest.mark.parametrize("level", list(LEVELS))
def test_correct_answer_matches_math(level):
    gen = RotationTaskGenerator(seed=1)
    for _ in range(100):
        task = gen.generate(level)
        expected = top_color(apply_sequence(IDENTITY, task.moves))
        assert task.correct_option == expected


@pytest.mark.parametrize("level", list(LEVELS))
def test_options_are_unique_and_right_count(level):
    gen = RotationTaskGenerator(seed=2)
    for _ in range(100):
        task = gen.generate(level)
        assert len(task.options) == LEVELS[level]["options"]
        assert len(set(task.options)) == len(task.options)


@pytest.mark.parametrize("level", list(LEVELS))
def test_number_of_moves_matches_level(level):
    low, high = LEVELS[level]["moves"]
    gen = RotationTaskGenerator(seed=3)
    for _ in range(100):
        assert low <= len(gen.generate(level).moves) <= high


@pytest.mark.parametrize("level", list(LEVELS))
def test_no_same_task_twice_in_a_row(level):
    gen = RotationTaskGenerator(seed=4)
    previous = gen.generate(level)
    for _ in range(200):
        current = gen.generate(level)
        assert current.moves != previous.moves
        previous = current


def test_same_seed_gives_same_tasks():
    a = RotationTaskGenerator(seed=5).generate("medium")
    b = RotationTaskGenerator(seed=5).generate("medium")
    assert a == b


def test_unknown_level_raises():
    with pytest.raises(ValueError):
        RotationTaskGenerator().generate("impossible")


def test_check_answer():
    task = RotationTaskGenerator(seed=6).generate("easy")
    assert check_answer(task, task.correct_index) is True
    wrong = (task.correct_index + 1) % len(task.options)
    assert check_answer(task, wrong) is False


@pytest.mark.parametrize("bad", [-1, 99, "1", None, True])
def test_check_answer_rejects_bad_input(bad):
    task = RotationTaskGenerator(seed=7).generate("easy")
    with pytest.raises(ValueError):
        check_answer(task, bad)