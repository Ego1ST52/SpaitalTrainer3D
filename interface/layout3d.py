"""Как ставить 3D-фигуры точно под элементы интерфейса (кнопки, подписи).

Используется режимами, где камера закреплена в (0, 0, -24) и смотрит прямо
(см. open_matching и open_projection в main.py)."""

import math

from ursina import camera, window

CAMERA_DISTANCE = 24


def ui_to_world(ui_x, ui_y):
    """Экранная точка -> точка сцены в плоскости z = 0 (где стоят фигуры).
    camera.fov - горизонтальный угол обзора, ширина экрана в единицах
    интерфейса равна window.aspect_ratio."""
    visible_width = 2 * CAMERA_DISTANCE * math.tan(math.radians(camera.fov / 2))
    units_per_ui = visible_width / window.aspect_ratio
    return ui_x * units_per_ui, ui_y * units_per_ui, 0


def fit_scale(cells, max_size):
    """Масштаб, при котором фигура не больше max_size по любой оси."""
    extent = max(max(c[i] for c in cells) - min(c[i] for c in cells) + 1
                 for i in range(3))
    return min(1.0, max_size / extent)
