"""Фигуры из кубиков как наборы целых координат. Без Ursina."""

from logic.rotations import all_orientations

NEIGHBORS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]

# Фиксированный порядок 24 поворотов
_ROTATIONS = sorted(all_orientations())


def apply_matrix(m, cell):
    x, y, z = cell
    return tuple(m[i][0] * x + m[i][1] * y + m[i][2] * z for i in range(3))


def normalize(cells):
    """Сдвинуть фигуру так, чтобы минимальные координаты стали нулями,
    и отсортировать клетки. Так одинаково расположенные фигуры равны."""
    cells = list(cells)
    mins = [min(c[i] for c in cells) for i in range(3)]
    return tuple(sorted(tuple(c[i] - mins[i] for i in range(3)) for c in cells))


def rotate_shape(cells, orientation):
    return normalize(apply_matrix(orientation, c) for c in cells)


def canonical(cells):
    """Каноническая форма: наименьший вариант среди 24 поворотов."""
    return min(rotate_shape(cells, m) for m in _ROTATIONS)


def mirror(cells):
    """Зеркальное отражение (по оси X). Поворотом его получить нельзя."""
    return normalize((-x, y, z) for x, y, z in cells)


def same_up_to_rotation(a, b):
    return canonical(a) == canonical(b)


def is_connected(cells):
    """Все ли кубики соединены гранями (поиск в глубину)."""
    cells = set(cells)
    start = next(iter(cells))
    seen = {start}
    stack = [start]
    while stack:
        x, y, z = stack.pop()
        for dx, dy, dz in NEIGHBORS:
            n = (x + dx, y + dy, z + dz)
            if n in cells and n not in seen:
                seen.add(n)
                stack.append(n)
    return len(seen) == len(cells)


def random_shape(rng, count):
    """Случайная связная фигура из count кубиков (рост от одного кубика)."""
    cells = {(0, 0, 0)}
    while len(cells) < count:
        bx, by, bz = rng.choice(sorted(cells))
        dx, dy, dz = rng.choice(NEIGHBORS)
        cells.add((bx + dx, by + dy, bz + dz))
    return normalize(cells)


def modify_shape(rng, cells):
    """Переставить один кубик на новое место. Результат связный, с тем же числом
    кубиков и НЕ равный исходной фигуре с учётом поворота. None, если не вышло."""
    cells = list(cells)
    for _ in range(60):
        removed = rng.choice(cells)
        rest = [c for c in cells if c != removed]
        if not is_connected(rest):
            continue
        rest_set = set(rest)
        free = sorted({(x + dx, y + dy, z + dz)
                       for x, y, z in rest for dx, dy, dz in NEIGHBORS}
                      - rest_set - {removed})
        added = rng.choice(free)
        candidate = normalize(rest + [added])
        if canonical(candidate) != canonical(cells):
            return candidate
    return None