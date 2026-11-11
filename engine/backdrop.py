"""Фон приложения: радиальное свечение и плавающие каркасные кубы."""

import math
import random

from PIL import Image
from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from core.preferences import prefs


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _gradient_image(width=320, height=180):
    """Картинка с мягким свечением: светлее у центра-слева, темнее к краям."""
    glow = _hex_to_rgb(settings.BACKDROP_GLOW)
    edge = _hex_to_rgb(settings.BACKDROP_EDGE)
    center_x, center_y = 0.38 * width, 0.42 * height
    reach = 0.75 * width
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            distance = math.hypot(x - center_x, (y - center_y) * 1.4) / reach
            t = min(1.0, distance) ** 1.3          # плавный спад к краям
            pixels[x, y] = tuple(round(g + (e - g) * t) for g, e in zip(glow, edge))
    return image


class Backdrop(Entity):
    """Большая картинка-фон далеко позади всех объектов. Привязана к камере,
    поэтому всегда заполняет экран. Создаётся один раз на всё приложение."""

    def __init__(self):
        super().__init__(parent=camera, model="quad", shader=unlit_shader, z=600,
                         scale=(480, 270), eternal=True)
        self.refresh()

    def refresh(self):
        """Перерисовать фон в цветах текущей темы."""
        texture = Texture(_gradient_image())
        texture.filtering = "bilinear"   # без «ступенек» между пикселями
        self.texture = texture


def wire_cube_mesh():
    """Каркас куба: 12 рёбер-отрезков."""
    corners = [Vec3(x, y, z) * 0.5 for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    edges = [(a, b) for a in range(8) for b in range(a + 1, 8)
             # ребро - если вершины отличаются ровно по одной оси
             if sum(corners[a][i] != corners[b][i] for i in range(3)) == 1]
    return Mesh(vertices=corners, triangles=edges, mode="line", thickness=2)


class FloatingCubes(Entity):
    """Несколько полупрозрачных каркасных кубов, которые медленно
    вращаются и покачиваются на фоне. Камера должна смотреть вдоль +z."""

    def __init__(self, count=9, seed=4):
        super().__init__()
        if prefs.reduce_motion:
            count = 0          # «меньше движения»: фон без плавающих кубов
        rng = random.Random(seed)
        mesh = wire_cube_mesh()
        accent = color.hex(settings.ACCENT)
        self.cubes = []
        for _ in range(count):
            depth = rng.uniform(18, 50)
            distance = depth + 20               # камера меню стоит в z = -20
            half_w = distance * 0.36             # половина видимой ширины
            half_h = distance * 0.2
            cube = Entity(parent=self, model=mesh, shader=unlit_shader,
                          position=(rng.uniform(-half_w, half_w),
                                    rng.uniform(-half_h, half_h), depth),
                          scale=rng.uniform(1.5, 4.5),
                          rotation=(rng.uniform(0, 360), rng.uniform(0, 360), 0),
                          color=color.rgba(accent.r, accent.g, accent.b,
                                           rng.uniform(0.08, 0.2)))
            cube.spin = Vec3(rng.uniform(-8, 8), rng.uniform(-12, 12), 0)
            cube.base_y = cube.y
            cube.phase = rng.uniform(0, math.tau)
            self.cubes.append(cube)

    def update(self):
        now = time.time()
        for cube in self.cubes:
            cube.rotation += cube.spin * time.dt
            cube.y = cube.base_y + math.sin(now * 0.4 + cube.phase) * 0.4
