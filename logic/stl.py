"""Экспорт фигуры из кубиков в STL - формат для 3D-принтера. Без Ursina.

Берём только ВНЕШНИЕ грани: грань между двумя соседними кубиками лежит
внутри фигуры и в модель не попадает. Каждая грань - два треугольника,
развёрнутые наружу (так требует формат). Получается замкнутая поверхность:
каждое ребро принадлежит ровно двум треугольникам - такую модель принтер
напечатает без ошибок.

Оси: у нас y - вверх, а в STL принято z - вверх, поэтому y и z меняем местами.
"""

from datetime import datetime
from pathlib import Path

DIRECTIONS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def exterior_faces(cells):
    """[(клетка, направление наружу)] для всех граней, не прижатых к соседу."""
    cells = set(cells)
    return [(cell, d) for cell in sorted(cells) for d in DIRECTIONS
            if (cell[0] + d[0], cell[1] + d[1], cell[2] + d[2]) not in cells]


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _to_stl_axes(point):
    x, y, z = point
    return (x, z, y)                     # y (вверх у нас) -> z (вверх в STL)


def triangles(cells, size=10.0):
    """Треугольники поверхности: [(нормаль, v1, v2, v3)] в миллиметрах."""
    result = []
    for (cx, cy, cz), d in exterior_faces(cells):
        axis = [i for i in range(3) if d[i] != 0][0]
        others = [i for i in range(3) if i != axis]
        corners = []
        for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):      # обход квадрата грани
            p = [cx, cy, cz]
            p[axis] += 1 if d[axis] > 0 else 0
            p[others[0]] += a
            p[others[1]] += b
            corners.append(_to_stl_axes(tuple(c * size for c in p)))
        normal = _to_stl_axes(d)
        for tri in ((corners[0], corners[1], corners[2]), (corners[0], corners[2], corners[3])):
            # Порядок вершин - против часовой стрелки, если смотреть снаружи
            if _dot(_cross(_sub(tri[1], tri[0]), _sub(tri[2], tri[0])), normal) < 0:
                tri = (tri[0], tri[2], tri[1])
            result.append((normal, *tri))
    return result


def to_ascii_stl(cells, name="figure", size=10.0):
    lines = [f"solid {name}"]
    for normal, *vertices in triangles(cells, size):
        lines.append(f"  facet normal {normal[0]} {normal[1]} {normal[2]}")
        lines.append("    outer loop")
        for v in vertices:
            lines.append(f"      vertex {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    return "\n".join(lines) + "\n"


def export_folder():
    """Папка для сохранённых фигур: «Документы\\SpatialTrainer3D»."""
    return Path.home() / "Documents" / "SpatialTrainer3D"


def export_stl(cells, folder=None):
    """Сохранить фигуру в файл и вернуть путь к нему."""
    folder = Path(folder) if folder else export_folder()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"фигура_{datetime.now():%Y-%m-%d_%H-%M-%S}.stl"
    path.write_text(to_ascii_stl(cells), encoding="ascii")
    return path
