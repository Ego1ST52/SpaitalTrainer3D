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
        expected = top_color(apply_sequence(IDENTITY, task.moves), target=task.target)
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

def test_easy_asks_only_top_and_hard_asks_all_sides():
    from logic.task_generator import TARGET_WORDS
    easy = {RotationTaskGenerator(seed=s).generate("easy").target for s in range(40)}
    hard = {RotationTaskGenerator(seed=s).generate("hard").target for s in range(80)}
    assert easy == {"+Y"}
    assert hard == set(TARGET_WORDS)
    task = RotationTaskGenerator(seed=4).generate("hard")
    assert task.question.endswith(f"окажется {task.target_word}?")


@pytest.mark.parametrize("level", list(LEVELS))
def test_wrong_options_are_explained_by_real_mistakes(level):
    from logic.task_generator import MISTAKE_TEXTS, mistaken_moves
    gen = RotationTaskGenerator(seed=6)
    for _ in range(100):
        task = gen.generate(level)
        assert task.kinds[task.correct_index] == "correct"
        assert task.kinds.count("correct") == 1
        wrong = mistaken_moves(task.moves)
        for index, kind in enumerate(task.kinds):
            if kind in MISTAKE_TEXTS:
                # вариант действительно получается при этой ошибке
                orientation = apply_sequence(IDENTITY, wrong[kind])
                assert task.options[index] == top_color(orientation, target=task.target)
                assert task.answer_tags(index) == (f"chose:{kind}",)
                assert MISTAKE_TEXTS[kind] in task.explain(index)
            else:
                assert task.answer_tags(index) == ()
                assert task.explain(index) is None


def test_most_tasks_offer_a_typical_mistake():
    gen = RotationTaskGenerator(seed=8)
    tasks = [gen.generate("medium") for _ in range(100)]
    with_mistake = sum(any(k not in ("correct", "random") for k in t.kinds) for t in tasks)
    assert with_mistake >= 90
