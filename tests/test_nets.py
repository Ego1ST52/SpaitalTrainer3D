import random

import pytest

from logic.nets import (NET_LEVELS, NetTaskGenerator, OPPOSITE, fold, is_net, normalize2d,
                        random_net, visible_triples)

CROSS = ((1, 0), (0, 1), (1, 1), (2, 1), (3, 1), (1, 2))      # классический «крест»
LINE = tuple((i, 0) for i in range(6))                         # 6 в ряд - не куб
SQUARE_2x3 = tuple((c, r) for c in range(2) for r in range(3))  # 2x3 - не куб


def test_cross_folds_into_cube():
    faces = fold(CROSS)
    assert faces is not None and set(faces.values()) == set(OPPOSITE)
    # В «кресте» клетки через одну в длинном ряду - противоположные грани
    assert faces[(0, 1)] == OPPOSITE[faces[(2, 1)]]
    assert faces[(1, 1)] == OPPOSITE[faces[(3, 1)]]
    assert faces[(1, 0)] == OPPOSITE[faces[(1, 2)]]


def test_non_nets_are_rejected():
    assert not is_net(LINE)
    assert not is_net(SQUARE_2x3)
    assert not is_net(((0, 0), (1, 0), (5, 5), (2, 0), (3, 0), (1, 1)))   # не связано
    assert not is_net(CROSS[:5])


def test_exactly_eleven_nets_exist():
    """Классический факт: у куба ровно 11 развёрток (с точностью до поворотов
    и отражений). Проверяем, что наш «складыватель» находит именно их."""
    def canonical(cells):
        variants = []
        for flip in (1, -1):
            pts = [(c * flip, r) for c, r in cells]
            for _ in range(4):
                pts = [(r, -c) for c, r in pts]
                variants.append(normalize2d(pts))
        return min(variants)

    rng = random.Random(1)
    found = {canonical(random_net(rng)) for _ in range(3000)}
    assert len(found) == 11


@pytest.mark.parametrize("level", list(NET_LEVELS))
def test_generated_tasks_are_correct(level):
    generator = NetTaskGenerator(seed=4)
    for _ in range(40):
        task = generator.generate(level)
        assert is_net(task.cells)
        assert len(set(task.options)) == len(task.options) == NET_LEVELS[level]["options"]
        letters = task.face_letters
        if task.kind == "opposite":
            marked_letter = task.letters[task.marked]
            marked_face = next(f for f, l in letters.items() if l == marked_letter)
            assert task.correct_option == letters[OPPOSITE[marked_face]]
            assert marked_letter not in task.options
        else:
            valid = visible_triples(letters)
            assert task.correct_option in valid                 # правильный складывается
            for i, option in enumerate(task.options):
                if i != task.correct_index:
                    assert option not in valid                  # остальные - нет


def test_visible_triples_count():
    faces = fold(CROSS)
    letters = {face: "АБВГДЕ"[i] for i, face in enumerate(faces.values())}
    # Куб можно повернуть 24 способами - и каждый даёт свою тройку
    assert len(visible_triples(letters)) == 24


def test_answer_tags():
    task = NetTaskGenerator(seed=5).generate("hard")
    wrong = next(i for i in range(len(task.options)) if i != task.correct_index)
    assert task.answer_tags(wrong)[0] in ("chose:mirror", "chose:opposite")
    assert task.answer_tags(task.correct_index) == ()
    assert task.tags == ("type:cube",)


def test_same_seed_same_tasks():
    a, b = NetTaskGenerator(seed=9), NetTaskGenerator(seed=9)
    assert [a.generate("hard") for _ in range(5)] == [b.generate("hard") for _ in range(5)]
