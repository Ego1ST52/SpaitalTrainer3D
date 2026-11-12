import pytest

from logic.projections import (PROJECTION_LEVELS, ProjectionTaskGenerator,
                               mirror2d, normalize2d, project, rotate2d)

# «Г»-образная фигура: три кубика по x внизу и один сверху справа,
# плюс один кубик сзади (по z) у левого края.
L_SHAPE = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0), (0, 0, 1))


def test_front_view():
    # Спереди не видно глубины: кубик сзади совпадает с кубиком спереди
    assert project(L_SHAPE, "front") == ((0, 0), (1, 0), (2, 0), (2, 1))


def test_top_view():
    # Сверху: ряд из трёх и кубик «вглубь» у левого края (выше на картинке)
    assert project(L_SHAPE, "top") == ((0, 0), (0, 1), (1, 0), (2, 0))


def test_right_view():
    # Справа: столбец высотой 2 спереди и кубик сзади (правее на картинке)
    assert project(L_SHAPE, "right") == ((0, 0), (0, 1), (1, 0))


def test_projection_ignores_position():
    moved = tuple((x + 5, y - 2, z + 7) for x, y, z in L_SHAPE)
    for view in ("front", "top", "right"):
        assert project(moved, view) == project(L_SHAPE, view)


def test_unknown_view():
    with pytest.raises(ValueError):
        project(L_SHAPE, "bottom")


def test_mirror_and_rotate():
    picture = normalize2d([(0, 0), (1, 0), (1, 1)])
    assert mirror2d(mirror2d(picture)) == picture
    assert rotate2d(rotate2d(rotate2d(rotate2d(picture)))) == picture
    assert mirror2d(picture) == ((0, 0), (0, 1), (1, 0))


@pytest.mark.parametrize("level", list(PROJECTION_LEVELS))
def test_generated_tasks_are_correct(level):
    generator = ProjectionTaskGenerator(seed=7)
    config = PROJECTION_LEVELS[level]
    for _ in range(40):
        task = generator.generate(level)
        # Правильный ответ - ровно проекция фигуры
        assert task.correct_option == project(task.shape, task.view)
        # Все варианты разные: правильный ровно один
        assert len(set(task.options)) == len(task.options) == config["options"]
        assert task.view in config["views"]
        low, high = config["cubes"]
        assert low <= len(task.shape) <= high


def test_no_same_task_twice_in_a_row():
    generator = ProjectionTaskGenerator(seed=3)
    previous = None
    for _ in range(50):
        task = generator.generate("easy")
        current = (task.shape, task.view)
        assert current != previous
        previous = current


def test_unknown_level():
    with pytest.raises(ValueError):
        ProjectionTaskGenerator().generate("expert")


@pytest.mark.parametrize("level", ["easy", "medium", "hard"])
def test_wrong_pictures_know_where_they_came_from(level):
    from logic.projections import mirror2d, rotate2d
    gen = ProjectionTaskGenerator(seed=21)
    for _ in range(60):
        task = gen.generate(level)
        assert task.kinds[task.correct_index] == "correct" and task.kinds.count("correct") == 1
        right = task.correct_option
        for picture, kind in zip(task.options, task.kinds):
            if kind.startswith("view:"):
                assert picture == project(task.shape, kind[5:])
            elif kind == "mirror":
                assert picture == mirror2d(right)
            elif kind == "rotated":
                assert picture in (rotate2d(right), rotate2d(rotate2d(right)))
        for i in range(len(task.options)):
            if i == task.correct_index:
                assert task.explain(i) is None and task.answer_tags(i) == ()
            else:
                assert task.explain(i)


def test_projection_mistake_tags_do_not_clash_with_matching():
    from logic.insights import MISTAKES
    assert MISTAKES["chose:mirror"][0] == "matching"
    assert MISTAKES["chose:mirror_view"][0] == "projection"
