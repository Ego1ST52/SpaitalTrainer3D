from collections import Counter

import pytest

from logic.stl import exterior_faces, export_stl, to_ascii_stl, triangles

SINGLE = [(0, 0, 0)]
PAIR = [(0, 0, 0), (1, 0, 0)]
L_SHAPE = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0), (0, 0, 1)]


def test_face_counts():
    assert len(exterior_faces(SINGLE)) == 6
    assert len(exterior_faces(PAIR)) == 10                  # общая грань - внутри
    assert len(triangles(L_SHAPE)) == 2 * len(exterior_faces(L_SHAPE))


@pytest.mark.parametrize("cells", [SINGLE, PAIR, L_SHAPE])
def test_surface_is_closed(cells):
    """Каждое ребро - ровно у двух треугольников: модель замкнутая,
    3D-принтер напечатает её без «дыр»."""
    edges = Counter()
    for _, a, b, c in triangles(cells):
        for p, q in ((a, b), (b, c), (c, a)):
            edges[frozenset((p, q))] += 1
    assert set(edges.values()) == {2}


def test_triangles_face_outward():
    """Порядок вершин согласован с нормалью, а нормаль смотрит наружу:
    от центра фигуры к грани (для выпуклого кубика это строго так)."""
    for normal, a, b, c in triangles(SINGLE):
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2],
                 ab[0] * ac[1] - ab[1] * ac[0])
        assert sum(cross[i] * normal[i] for i in range(3)) > 0
        center = [(a[i] + b[i] + c[i]) / 3 - 5 for i in range(3)]     # центр кубика 10 мм
        assert sum(center[i] * normal[i] for i in range(3)) > 0


def test_ascii_format_and_file(tmp_path):
    text = to_ascii_stl(PAIR, name="pair")
    assert text.startswith("solid pair") and text.rstrip().endswith("endsolid pair")
    assert text.count("facet normal") == 20
    path = export_stl(PAIR, tmp_path)
    assert path.suffix == ".stl" and path.read_text(encoding="ascii") == to_ascii_stl(PAIR)
