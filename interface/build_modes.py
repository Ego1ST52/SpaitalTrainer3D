"""Режимы-стройки на основе «Конструирования»:
  «Симметрия» - достроить половину фигуры зеркально;
  «Собери по трём видам» - собрать фигуру по чертежу.
Вся сборка (клик, Shift+клик, отмена, проверка, итоги) - из ConstructionGameScreen,
здесь только то, чем режимы отличаются."""

import textwrap

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from interface.construction_interface import (ConstructionGameScreen, PANEL_LEFT, PANEL_X,
                                              PREVIEW_Y)
from interface.ui_kit import FRONT, label
from logic.construction import GRID_HALF
from logic.projections import VIEWS
from logic.symmetry import FixedBuild, SymmetryTaskGenerator, check_symmetry, symmetry_diff
from logic.three_views import (VIEW_ORDER, ThreeViewsTaskGenerator, check_views,
                               views_hint, wrong_views)

PLANE_HEIGHT = 4             # высота «зеркала» в клетках
GIVEN_COLOR = "#94a3b8"       # кубики, которые даны заранее (их не убрать)
SIDE_LABEL_SCALE = 7          # подписи сторон площадки в 3D


def side_labels(accent):
    """Подписи «спереди» и «справа» на полу у края площадки: чертёж читают
    с этих сторон. Лежат на полу, поэтому не загораживают постройку."""
    holder = Entity()
    edge = GRID_HALF - 0.1
    tint = color.hex(accent)
    for text, position in (("спереди", (0, -0.48, -edge)), ("справа", (edge, -0.48, 0))):
        Text(text, parent=holder, position=position, rotation_x=90, origin=(0, 0),
             scale=SIDE_LABEL_SCALE, color=color.rgba(tint.r, tint.g, tint.b, 0.8))
    return holder


class SymmetryGameScreen(ConstructionGameScreen):
    MODE = "symmetry"
    SAMPLE_TITLE = "Зеркальная плоскость"

    def make_generator(self, seed):
        return SymmetryTaskGenerator(seed=seed)

    def make_build(self):
        return FixedBuild(self.task.given, self.task.max_cubes)

    def show_sample(self):
        self.preview_hint.enabled = False
        text = ("Прозрачная стена на площадке - зеркало. Каждый кубик отражается "
                "в нём на таком же расстоянии по другую сторону. Серые кубики "
                "даны заранее, их не убрать.")
        self.sample_objects.append(label(textwrap.fill(text, 34), (PANEL_LEFT, 0.24), 0.8,
                                         "text", origin=(-0.5, 0.5)))
        # Сама плоскость: полупрозрачная стена с сеткой между клетками
        accent = color.hex(self.accent)
        size = 2 * GRID_HALF + 1
        height = PLANE_HEIGHT
        plane = Entity(position=(-0.5, height / 2 - 0.5, 0), rotation_y=90)
        if self.task.plane == "z":
            plane.position = (0, height / 2 - 0.5, -0.5)
            plane.rotation_y = 0
        Entity(parent=plane, model="quad", scale=(size, height), double_sided=True,
               color=color.rgba(accent.r, accent.g, accent.b, 0.12), shader=unlit_shader)
        Entity(parent=plane, model=Grid(size, height), scale=(size, height),
               color=color.rgba(accent.r, accent.g, accent.b, 0.35), shader=unlit_shader,
               double_sided=True)
        self.sample_objects.append(plane)

    def block_color(self, cell):
        return GIVEN_COLOR if cell in self.task.given else self.accent

    def is_correct(self):
        return check_symmetry(self.build.cells, self.task.given, self.task.plane)

    def diff_cells(self):
        extra, missing = symmetry_diff(self.build.cells, self.task.given, self.task.plane)
        return set(self.build.cells) - extra, extra, missing

    def mistake_message(self):
        return self._show_diff()

    def counter_text(self):
        added = len(self.build.cells) - len(self.task.given)
        return f"Поставлено: {added} из {self.task.missing_count}"


class ThreeViewsGameScreen(ConstructionGameScreen):
    MODE = "views"
    SAMPLE_TITLE = "Чертёж"
    PICTURE = 0.11            # размер картинки вида
    STEP = 0.14               # расстояние между видами

    def make_generator(self, seed):
        return ThreeViewsTaskGenerator(seed=seed)

    def show_sample(self):
        self.preview_hint.enabled = False
        self.view_labels = {}
        for i, view in enumerate(VIEW_ORDER):
            x = PANEL_X + (i - 1) * self.STEP
            holder = Entity(parent=camera.ui, position=(x, PREVIEW_Y + 0.02))
            self._draw_view(holder, self.task.views[view])
            self.view_labels[view] = label(VIEWS[view], (0, -self.PICTURE / 2 - 0.035), 0.8,
                                           "muted", origin=(0, 0), parent=holder)
            self.sample_objects.append(holder)
        self.sample_objects.append(side_labels(self.accent))

    def _draw_view(self, holder, picture):
        """Картинка вида: клетки на тёмной подложке."""
        cols = max(c for c, _ in picture) + 1
        rows = max(r for _, r in picture) + 1
        cell = min(0.026, self.PICTURE / max(cols, rows))
        Entity(parent=holder, model="quad", shader=unlit_shader, z=FRONT / 2,
               scale=self.PICTURE + 0.012, color=color.hex(settings.SURFACE_HOVER))
        for c, r in picture:
            Entity(parent=holder, model="quad", shader=unlit_shader,
                   position=((c - (cols - 1) / 2) * cell, (r - (rows - 1) / 2) * cell, FRONT),
                   scale=cell * 0.86, color=color.hex(self.accent))

    def is_correct(self):
        return check_views(self.build.cells, self.task)

    def mistake_message(self):
        # Ответов может быть несколько, поэтому не показываем «правильные кубики»,
        # а отмечаем, какие виды не совпали
        for block in self.blocks.values():
            block.set_color(settings.WRONG_COLOR)
        return views_hint(self.build.cells, self.task)

    def on_checked(self, correct):
        wrong = wrong_views(self.build.cells, self.task)
        for view, text in self.view_labels.items():
            ok = view not in wrong
            text.color = color.hex(settings.CORRECT_COLOR if ok else settings.WRONG_COLOR)

    def counter_text(self):
        return f"Поставлено: {len(self.build.cells)}  (можно до {self.build.max_cubes})"
