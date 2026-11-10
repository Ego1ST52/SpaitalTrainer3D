"""Математика ориентации куба. Здесь нет ничего от Ursina:
этот модуль можно полностью проверить автотестами."""

from collections import deque

# Матрица = кортеж из трёх строк по три целых числа
IDENTITY = ((1, 0, 0), (0, 1, 0), (0, 0, 1))

# Поворот на +90 градусов вокруг мировой оси (правило правой руки)
_QUARTER_TURNS = {
    "x": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    "y": ((0, 0, 1), (0, 1, 0), (-1, 0, 0)),
    "z": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
}

# Нормали граней куба в исходном положении
FACE_NORMALS = {
    "+X": (1, 0, 0), "-X": (-1, 0, 0),
    "+Y": (0, 1, 0), "-Y": (0, -1, 0),
    "+Z": (0, 0, 1), "-Z": (0, 0, -1),
}
_NORMAL_TO_FACE = {normal: name for name, normal in FACE_NORMALS.items()}


def multiply(a, b):
    """Произведение матриц a * b (сначала b, потом a)."""
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def transpose(m):
    """Транспонирование. Для матрицы поворота это обратный поворот."""
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def determinant(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def rotate(orientation, axis, angle):
    """Повернуть куб на angle градусов вокруг мировой оси 'x', 'y' или 'z'.
    angle должен быть кратен 90 (может быть отрицательным).
    Возвращает НОВУЮ ориентацию, старая не меняется."""
    if axis not in _QUARTER_TURNS:
        raise ValueError(f"Неизвестная ось: {axis!r}")
    if angle % 90 != 0:
        raise ValueError(f"Угол должен быть кратен 90: {angle}")

    turns = (angle // 90) % 4  # сколько раз по +90 (отрицательные -> положительные)
    step = _QUARTER_TURNS[axis]
    result = orientation
    for _ in range(turns):
        result = multiply(step, result)  # мировой поворот применяется слева
    return result


def apply_sequence(orientation, moves):
    """Применить список поворотов [(ось, угол), ...] по порядку."""
    for axis, angle in moves:
        orientation = rotate(orientation, axis, angle)
    return orientation


def all_orientations():
    """Все 24 ориентации куба (обход в ширину)."""
    found = {IDENTITY}
    queue = deque([IDENTITY])
    while queue:
        current = queue.popleft()
        for axis in "xyz":
            nxt = rotate(current, axis, 90)
            if nxt not in found:
                found.add(nxt)
                queue.append(nxt)
    return found


def face_direction(orientation, face):
    """Куда сейчас смотрит грань face (например '+Z'): возвращает '+X', '-Y' и т.д."""
    nx, ny, nz = FACE_NORMALS[face]
    vector = tuple(
        orientation[i][0] * nx + orientation[i][1] * ny + orientation[i][2] * nz
        for i in range(3)
    )
    return _NORMAL_TO_FACE[vector]
def face_at(orientation, direction):
    """Какая грань куба сейчас смотрит в направление direction ('+X', '-Z' и т.д.).
    Обратная операция к face_direction."""
    for face in FACE_NORMALS:
        if face_direction(orientation, face) == direction:
            return face
    raise ValueError(f"Неизвестное направление: {direction!r}")