import pytest

from logic.construction import (Build, CONSTRUCTION_LEVELS, ConstructionTaskGenerator,
                                build_hint, check_build, extent, MAX_EXTENT,
                                MAX_HEIGHT, GRID_HALF)
from logic.rotations import all_orientations
from logic.shapes import canonical, rotate_shape, mirror

L_SHAPE = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0))


def test_exact_copy_matches():
    assert check_build(L_SHAPE, L_SHAPE)


def test_any_rotation_and_position_matches():
    for orientation in all_orientations():
        rotated = rotate_shape(L_SHAPE, orientation)
        moved = [(x - 3, y, z + 2) for x, y, z in rotated]
        assert check_build(moved, L_SHAPE)


def test_mirror_does_not_match_when_chiral():
    chiral = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1))   # «винтовая» фигура
    assert canonical(mirror(chiral)) != canonical(chiral)
    assert not check_build(mirror(chiral), chiral)


def test_wrong_count_or_shape_does_not_match():
    assert not check_build([], L_SHAPE)
    assert not check_build(L_SHAPE[:3], L_SHAPE)
    assert not check_build(((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)), L_SHAPE)


def test_disconnected_build_does_not_match():
    apart = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 2, 0))
    assert not check_build(apart, L_SHAPE)
    assert "распалась" in build_hint(apart, L_SHAPE)


def test_hints():
    assert "ничего" in build_hint([], L_SHAPE)
    assert "Не хватает" in build_hint(L_SHAPE[:2], L_SHAPE)
    assert "Лишние" in build_hint(L_SHAPE + ((5, 0, 0),), L_SHAPE)
    straight = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0))
    assert "форма другая" in build_hint(straight, L_SHAPE)


def test_build_place_rules():
    build = Build(max_cubes=3)
    assert not build.can_add((0, 1, 0))          # в воздухе нельзя
    assert build.add((0, 0, 0))                   # на полу можно
    assert not build.add((0, 0, 0))               # место занято
    assert build.add((0, 1, 0))                   # на другом кубике можно
    assert not build.can_add((GRID_HALF + 1, 0, 0))   # за площадкой нельзя
    assert not build.can_add((0, MAX_HEIGHT, 0))
    assert build.add((1, 0, 0))
    assert not build.can_add((2, 0, 0))           # лимит 3 кубика


def test_undo_and_clear():
    build = Build(max_cubes=10)
    build.add((0, 0, 0))
    build.add((1, 0, 0))
    build.remove((0, 0, 0))
    assert build.cells == {(1, 0, 0)}
    assert build.undo()                           # вернули удалённый
    assert build.cells == {(0, 0, 0), (1, 0, 0)}
    build.clear()
    assert build.cells == set()
    assert build.undo() and build.undo()          # очистку можно отменить
    assert build.cells == {(0, 0, 0), (1, 0, 0)}
    assert build.undo() and build.undo()
    assert not build.undo()                       # отменять больше нечего


@pytest.mark.parametrize("level", list(CONSTRUCTION_LEVELS))
def test_generator_levels(level):
    generator = ConstructionTaskGenerator(seed=5)
    low, high = CONSTRUCTION_LEVELS[level]["cubes"]
    previous = None
    for _ in range(200):
        task = generator.generate(level)
        assert low <= len(task.target) <= high
        assert check_build(task.target, task.target)
        # образец всегда помещается на площадку и по высоте
        assert extent(task.target) <= MAX_EXTENT
        assert MAX_EXTENT <= min(2 * GRID_HALF + 1, MAX_HEIGHT)
        assert canonical(task.target) != previous
        previous = canonical(task.target)


def test_unknown_level():
    with pytest.raises(ValueError):
        ConstructionTaskGenerator().generate("expert")


def test_diff_of_correct_build_is_clean():
    from logic.construction import build_diff
    from logic.rotations import rotate
    from logic.shapes import apply_matrix
    target = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1))
    turned = {apply_matrix(rotate(((1, 0, 0), (0, 1, 0), (0, 0, 1)), "y", 90), c) for c in target}
    build = {(x + 1, y, z) for x, y, z in turned}
    matched, extra, missing = build_diff(build, target)
    assert matched == build and not extra and not missing


def test_diff_finds_extra_and_missing_cube():
    from logic.construction import build_diff
    target = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0))          # «Г» из 4 кубиков
    build = {(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0), (2, 0, 1)}  # 3 верных + 2 лишних
    matched, extra, missing = build_diff(build, target)
    assert len(matched) == 4 and extra == {(2, 0, 1)} and not missing
    assert len(matched) + len(missing) == len(target)
    assert extra == build - matched
    # Достроив недостающее и убрав лишнее, получаем верную фигуру
    fixed = (build - extra) | missing
    assert check_build(fixed, target)


def test_diff_prefers_placement_inside_the_grid():
    from logic.construction import GRID_HALF, MAX_HEIGHT, build_diff
    target = ((0, 0, 0), (0, 1, 0), (0, 2, 0))                       # столбик
    build = {(0, 0, 0)}
    matched, extra, missing = build_diff(build, target)
    assert matched == build and not extra
    assert all(0 <= y < MAX_HEIGHT and abs(x) <= GRID_HALF and abs(z) <= GRID_HALF
               for x, y, z in missing)


def test_diff_random_builds_always_fixable():
    import random
    from logic.construction import ConstructionTaskGenerator, build_diff
    rng = random.Random(4)
    gen = ConstructionTaskGenerator(seed=4)
    for _ in range(40):
        task = gen.generate("medium")
        build = {(rng.randint(-1, 1), rng.randint(0, 1), rng.randint(-1, 1)) for _ in range(5)}
        matched, extra, missing = build_diff(build, task.target)
        assert matched | extra == build and not (matched & extra)
        assert len(matched) + len(missing) == len(task.target)
        assert check_build((build - extra) | missing, task.target)
