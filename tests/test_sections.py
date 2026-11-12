from fractions import Fraction as F

import pytest

from logic.sections import (EDGES, SECTION_LEVELS, SHAPE_FAMILIES, SIDE_NAMES,
                            SectionTaskGenerator, classify, section_polygon)

H = F(1, 2)


def test_cube_has_twelve_edges():
    assert len(EDGES) == 12


def test_corner_cut_is_equilateral_triangle():
    # Плоскость через три соседние с вершиной (0,0,0) вершины
    poly = section_polygon((1, 0, 0), (0, 1, 0), (0, 0, 1))
    assert len(poly) == 3 and classify(poly) == "Правильный треугольник"


def test_diagonal_cut_is_rectangle():
    # Через два противоположных ребра - прямоугольник (не квадрат: стороны 1 и √2)
    poly = section_polygon((0, 0, 0), (0, 0, 1), (1, 1, 0))
    assert classify(poly) == "Прямоугольник"


def test_midplane_parallel_to_face_is_square():
    poly = section_polygon((H, 0, 0), (H, 1, 0), (H, 0, 1))
    assert len(poly) == 4 and classify(poly) == "Квадрат"


def test_regular_hexagon_through_edge_midpoints():
    # Плоскость x + y + z = 3/2 через середины рёбер - правильный шестиугольник
    poly = section_polygon((1, H, 0), (H, 1, 0), (0, 1, H))
    assert len(poly) == 6 and classify(poly) == "Правильный шестиугольник"


def test_trapezoid():
    trapezoid = section_polygon((H, 0, 0), (0, H, 0), (1, 0, 1))
    assert len(trapezoid) == 4 and classify(trapezoid) == "Трапеция"


def test_pentagons_exist_and_are_named():
    generator = SectionTaskGenerator(seed=1)
    pentagons = [t.polygon for t in (generator.generate("medium") for _ in range(200))
                 if len(t.polygon) == 5]
    assert pentagons                                  # средний уровень даёт пятиугольники
    assert all(classify(p) == "Пятиугольник" for p in pentagons)


def test_rhombus_exact():
    # Плоскость через вершины (0,0,0) и (1,1,1) и середину ребра - ромб
    poly = section_polygon((0, 0, 0), (1, 1, 1), (1, 0, H))
    assert len(poly) == 4 and classify(poly) == "Ромб"


def test_degenerate_planes_are_rejected():
    assert section_polygon((0, 0, 0), (H, 0, 0), (1, 0, 0)) is None     # одна прямая
    assert section_polygon((0, 0, 0), (1, 0, 0), (0, 1, 0)) is None     # это грань z=0


@pytest.mark.parametrize("level", list(SECTION_LEVELS))
def test_generated_tasks_are_consistent(level):
    generator = SectionTaskGenerator(seed=11)
    sides_seen = set()
    for _ in range(60):
        task = generator.generate(level)
        assert 3 <= len(task.polygon) <= 6
        assert len(set(task.options)) == len(task.options)
        if task.kind == "sides":
            assert task.correct_option == SIDE_NAMES[len(task.polygon)]
        else:
            assert task.correct_option == classify(task.polygon)
            assert len(task.options) == SECTION_LEVELS["hard"]["options"]
        sides_seen.add(len(task.polygon))
        # Каждая вершина сечения лежит на поверхности куба
        for p in task.polygon:
            assert all(0 <= c <= 1 for c in p) and any(c in (0, 1) for c in p)
    assert len(sides_seen) >= 2                   # задания разнообразные


def test_every_shape_name_is_known():
    names = {n for family in SHAPE_FAMILIES.values() for n in family}
    generator = SectionTaskGenerator(seed=3)
    for _ in range(80):
        assert classify(generator.generate("hard").polygon) in names
