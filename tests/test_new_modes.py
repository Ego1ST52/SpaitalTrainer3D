"""Новые режимы: «Найди повороты», «Симметрия», «Собери по трём видам»."""

import pytest

from logic.construction import GRID_HALF, Build
from logic.reverse_rotations import ReverseTaskGenerator, moves_text
from logic.rotations import IDENTITY, apply_sequence
from logic.shapes import is_connected
from logic.symmetry import (FixedBuild, SymmetryTaskGenerator, check_symmetry, mirrored_part,
                            reflect, symmetry_diff)
from logic.three_views import (ThreeViewsTaskGenerator, ThreeViewsTask, check_views,
                               views_hint, wrong_views)
from logic.training_code import make_code, parse_code

LEVELS = ("easy", "medium", "hard")


# ---------- «Найди повороты» ----------
@pytest.mark.parametrize("level", LEVELS)
def test_reverse_only_correct_option_gives_target(level):
    """Ровно один вариант приводит куб в положение «стало» - и это правильный."""
    gen = ReverseTaskGenerator(seed=3)
    for _ in range(60):
        task = gen.generate(level)
        reached = [apply_sequence(IDENTITY, option) for option in task.options]
        assert reached[task.correct_index] == task.target != IDENTITY
        assert reached.count(task.target) == 1
        assert len(set(reached)) == len(reached)          # все варианты различимы
        assert len({moves_text(o) for o in task.options}) == len(task.options)


def test_reverse_explains_typical_mistakes():
    gen = ReverseTaskGenerator(seed=1)
    seen = set()
    for _ in range(80):
        task = gen.generate("medium")
        for i, kind in enumerate(task.kinds):
            if i == task.correct_index:
                assert task.explain(i) is None and task.answer_tags(i) == ()
            else:
                assert task.explain(i)
                if kind != "random":
                    assert task.answer_tags(i) == (f"chose:rev_{kind}",)
                    seen.add(kind)
    assert {"reversed", "inverted"} <= seen


def test_reverse_mistake_tags_have_advice():
    from logic.insights import MISTAKES
    for kind in ("reversed", "inverted", "skipped"):
        assert MISTAKES[f"chose:rev_{kind}"][0] == "reverse"


def test_moves_text():
    assert moves_text((("x", 90), ("y", -90))) == "X +90°,  Y -90°"


# ---------- «Симметрия» ----------
def test_reflect_crosses_the_plane_between_cells():
    assert reflect((0, 1, 2), "x") == (-1, 1, 2)
    assert reflect((2, 0, 0), "x") == (-3, 0, 0)
    assert reflect((1, 0, 0), "z") == (1, 0, -1)
    assert reflect(reflect((2, 3, -1), "z"), "z") == (2, 3, -1)


@pytest.mark.parametrize("level", LEVELS)
def test_symmetry_tasks_fit_the_grid_and_are_buildable(level):
    gen = SymmetryTaskGenerator(seed=7)
    for _ in range(60):
        task = gen.generate(level)
        target = task.target
        assert all(Build.in_bounds(c) for c in target)
        assert is_connected(target)                         # половина касается зеркала
        assert len(target) == 2 * len(task.given)
        # Правильную фигуру можно собрать по правилам площадки
        build = FixedBuild(task.given, task.max_cubes)
        missing = sorted(mirrored_part(task.given, task.plane), key=lambda c: c[1])
        for _ in range(len(missing)):
            for cell in missing:
                build.add(cell)
        assert check_symmetry(build.cells, task.given, task.plane)


def test_symmetry_given_cubes_stay():
    given = ((0, 0, 0), (1, 0, 0))
    build = FixedBuild(given, 10)
    build.add((-1, 0, 0))
    assert not build.remove((0, 0, 0))
    build.clear()
    assert build.cells == set(given)
    assert not check_symmetry(build.cells, given, "x")


def test_symmetry_diff():
    given = ((0, 0, 0), (1, 0, 0))
    extra, missing = symmetry_diff({(0, 0, 0), (1, 0, 0), (-1, 0, 0), (-1, 1, 0)}, given, "x")
    assert extra == {(-1, 1, 0)} and missing == {(-2, 0, 0)}


# ---------- «Собери по трём видам» ----------
@pytest.mark.parametrize("level", LEVELS)
def test_views_shape_itself_is_accepted_anywhere(level):
    gen = ThreeViewsTaskGenerator(seed=2)
    for _ in range(40):
        task = gen.generate(level)
        shifted = [(x - 1, y, z - 1) for x, y, z in task.shape]
        assert all(abs(x) <= GRID_HALF and abs(z) <= GRID_HALF for x, _, z in shifted)
        assert check_views(shifted, task)


def test_views_accept_any_shape_with_the_same_drawing():
    """По трём видам фигура восстанавливается не единственным способом -
    засчитывается любая связная постройка с тем же чертежом."""
    task = ThreeViewsTask("easy", ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1),
                                   (0, 1, 0)))
    other = [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1), (0, 1, 0), (0, 1, 1)]
    assert wrong_views(other, task) == ["right"]       # справа видна лишняя клетка
    twin = [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1), (0, 1, 1)]
    assert check_views(twin, task) is False            # верхний кубик дальше - другой вид справа
    assert wrong_views([(0, 0, 0)], task) == ["front", "top", "right"]


def test_views_hint_names_wrong_views():
    task = ThreeViewsTask("easy", ((0, 0, 0), (0, 1, 0)))
    assert views_hint([(0, 0, 0)], task) == "Не совпали виды спереди и справа."
    square = ThreeViewsTask("easy", ((0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1)))
    corner = [(0, 0, 0), (1, 0, 0), (0, 0, 1)]          # спереди и справа - как квадрат
    assert views_hint(corner, square) == "Не совпал вид сверху."
    assert views_hint([(0, 0, 0), (2, 0, 0)], task).startswith("Фигура распалась")
    assert views_hint([], task) == "Вы ещё ничего не построили."


# ---------- коды тренировок для режимов 10-12 ----------
@pytest.mark.parametrize("mode", ["reverse", "symmetry", "views"])
def test_two_digit_mode_codes_round_trip(mode):
    code = make_code(mode, "hard", 42)
    assert len(code) == 8 and parse_code(code) == (mode, "hard", 42)
    assert parse_code(code.replace("-", " ")) == (mode, "hard", 42)


def test_old_codes_still_work():
    assert parse_code("31-4821") == ("projection", "easy", 4821)
    with pytest.raises(ValueError):
        parse_code("131-4821")            # режима 13 нет
