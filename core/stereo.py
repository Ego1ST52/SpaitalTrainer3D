"""Стерео-3D для красно-синих (анаглифных) очков.

Panda3D умеет рисовать сцену дважды - для левого и правого глаза - и
смешивать картинки: левый глаз в красном канале, правый в голубом. Через
очки каждый глаз видит свою картинку, и мозг складывает их в объём.

Режим включается ТОЛЬКО до создания окна, поэтому main.py читает
настройку последнего игрока заранее, ещё до Ursina().
"""

import sqlite3

from data.database import Database

# Расстояние между «глазами» и расстояние, на котором картинка совпадает
# с экраном (в единицах сцены). Камера в игре стоит в 10-22 единицах от
# фигуры, так что фигура слегка «выходит» из экрана, но глаза не устают.
EYE_DISTANCE = 0.25
SCREEN_DISTANCE = 16.0
PRC_LINES = "red-blue-stereo 1\nred-blue-stereo-colors red cyan\n"


def wanted(db_path):
    """Включено ли стерео у игрока, который играл последним."""
    try:
        db = Database(db_path)
    except (sqlite3.Error, OSError):
        return False
    try:
        last = db.get_state("last_user")
        return last is not None and db.get_settings(last).get("stereo") is True
    except sqlite3.Error:
        return False
    finally:
        db.close()


def enable_before_window():
    """Попросить Panda3D открыть окно в стерео. Вызывать до Ursina()."""
    from panda3d.core import loadPrcFileData
    loadPrcFileData("stereo", PRC_LINES)


def configure(camera):
    """Глубина стерео для 3D-камеры (интерфейс остаётся плоским)."""
    lens = camera.perspective_lens
    lens.set_interocular_distance(EYE_DISTANCE)
    lens.set_convergence_distance(SCREEN_DISTANCE)
