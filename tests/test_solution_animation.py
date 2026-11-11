"""Показ решения в режиме «Вращение» не должен терять повороты,
даже если кадры идут с большими паузами («подвисание» компьютера)."""

import time

import pytest

from logic.rotations import IDENTITY, apply_sequence

ursina = pytest.importorskip("ursina")

MOVES = [("z", 90), ("y", 180), ("z", 180), ("x", 90), ("y", -90)]


def is_right_angle(value):
    return abs(value / 90 - round(value / 90)) < 0.01


def test_all_moves_applied_despite_slow_frames(ursina_app):
    from engine.objects import ColoredCube, dispose

    cube = ColoredCube()
    finished = []
    cube.play_moves(MOVES, on_done=lambda: finished.append(True))

    for _ in range(60):              # кадры с паузой 0.5 с между ними
        if finished:
            break
        time.sleep(0.5)
        ursina_app.step()

    try:
        assert finished, "решение не доиграло до конца"
        assert cube.orientation == apply_sequence(IDENTITY, MOVES)
        # Куб на экране стоит ровно: каждый угол кратен 90 градусам
        assert all(is_right_angle(v) for v in cube.world_rotation)
    finally:
        dispose(cube)
