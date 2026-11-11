import textwrap
from time import perf_counter

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.objects import ShadedBlock, ShadedShape, dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import label, mode_color, Panel, TopBar, UIButton
from logic.construction import Build, ConstructionTaskGenerator, GRID_HALF, \
    build_hint, check_build
from logic.session import TrainingSession

LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}

PANEL_X = 0.62
PANEL_WIDTH = 0.44
PANEL_LEFT = PANEL_X - PANEL_WIDTH / 2 + 0.03
PREVIEW_Y = 0.14
REMOVE_HINT_COLOR = "#f87171"      # кубик под курсором при Shift (будет удалён)


class ConstructionGameScreen(BaseScreen):
    """Режим 4: собрать из кубиков фигуру по образцу.
    Клик - поставить кубик, Shift+клик - убрать, Ctrl+Z - отменить."""

    def __init__(self, manager, level="easy"):
        super().__init__(manager)
        self.accent = mode_color("construction")
        self.generator = ConstructionTaskGenerator()
        self.session = self._new_session(level)
        self.task = None
        self.build = None
        self.blocks = {}            # клетка -> 3D-кубик
        self.task_started = 0.0
        self.answered = False
        self.preview = None

        # Площадка: тёмная плита с сеткой. Коллайдер нужен, чтобы мышь «видела» пол.
        size = 2 * GRID_HALF + 1
        self.ground = self.own(Entity(model="cube", scale=(size, 0.1, size), y=-0.55,
                                      color=color.hex(settings.FLOOR_COLOR),
                                      shader=unlit_shader, collider="box"))
        grid_color = color.hex(self.accent)
        self.own(Entity(model=Grid(size, size), rotation_x=90, scale=size, y=-0.495,
                        color=color.rgba(grid_color.r, grid_color.g, grid_color.b, 0.3),
                        shader=unlit_shader))
        # «Призрак» - показывает, куда встанет кубик
        self.ghost = self.own(Entity(model="cube", scale=0.98, enabled=False,
                                     color=color.rgba(grid_color.r, grid_color.g,
                                                      grid_color.b, 0.35),
                                     shader=unlit_shader))

        self.top_bar = self.own(TopBar("construction", self.go_back,
                                       settings.CONSTRUCTION_LENGTH))
        self.own(Panel(PANEL_WIDTH, 0.78, position=(PANEL_X, -0.06)))
        self.own(label("Образец", (PANEL_LEFT, 0.29), 0.8, "muted"))
        self.question = self.own(label("", (PANEL_LEFT, 0.005), 0.95, "strong"))
        self.counter = self.own(label("", (PANEL_LEFT, -0.07), 0.8, "muted"))

        self.own(UIButton("Отменить", self.undo, position=(PANEL_X - 0.105, -0.135),
                          scale=(0.19, 0.055), text_size=0.8))
        self.own(UIButton("Очистить", self.clear, position=(PANEL_X + 0.105, -0.135),
                          scale=(0.19, 0.055), text_size=0.8, variant="ghost"))
        self.feedback = self.own(label("", (PANEL_LEFT, -0.25), 0.85))
        self.action_button = self.own(UIButton("Проверить", self.check_or_next,
                                               position=(PANEL_X, -0.415),
                                               scale=(PANEL_WIDTH - 0.06, 0.06),
                                               variant="primary"))

        self.own(label("Клик - поставить кубик  •  Shift+клик - убрать  •  Ctrl+Z - отменить"
                       "  •  правая кнопка мыши - вращать камеру, колесо - приблизить",
                       (window.top_left.x + 0.05, -0.455), 0.75, "muted"))
        self.new_task()

    def _new_session(self, level):
        return TrainingSession("construction", level, settings.CONSTRUCTION_LENGTH)

    # ---------- задания ----------
    def new_task(self):
        self.task = self.generator.generate(self.session.level)
        self.build = Build(self.task.max_cubes)
        self.answered = False
        self.task_started = perf_counter()
        for block in self.blocks.values():
            dispose(block)
        self.blocks = {}

        if self.preview:
            dispose(self.preview)
        extent = max(max(c[i] for c in self.task.target) - min(c[i] for c in self.task.target)
                     for i in range(3)) + 1
        self.preview = ShadedShape(self.task.target, self.accent,
                                   position=(PANEL_X, PREVIEW_Y, -0.3),
                                   scale=min(0.055, 0.2 / extent), rotation_x=-25)

        self.question.text = textwrap.fill(self.task.question, 28)
        self.feedback.text = ""
        self.action_button.text = "Проверить"
        self._refresh()

    def _refresh(self):
        self.counter.text = (f"Поставлено: {len(self.build.cells)} из "
                             f"{len(self.task.target)}  (можно до {self.build.max_cubes})")
        s = self.session
        self.top_bar.update_state(s.level, s.results, self.answered, s.points)

    # ---------- кубики ----------
    def _sync_blocks(self):
        """Привести 3D-кубики в соответствие с постройкой (после отмены и т.п.)."""
        for cell in list(self.blocks):
            if cell not in self.build.cells:
                dispose(self.blocks.pop(cell))
        for cell in self.build.cells:
            if cell not in self.blocks:
                block = ShadedBlock(self.accent, position=cell)
                block.cell = cell
                self.blocks[cell] = block
        self._refresh()

    def _hovered_block(self):
        hit = mouse.hovered_entity
        return hit if hit is not None and hasattr(hit, "cell") else None

    def _target_cell(self):
        """Клетка, куда встанет кубик при клике, или None."""
        hit = mouse.hovered_entity
        if hit is None:
            return None
        if hasattr(hit, "cell"):         # грань другого кубика: ставим рядом с ней
            normal = mouse.world_normal
            return tuple(c + round(n) for c, n in zip(hit.cell, normal))
        if hit is self.ground:           # пол: ближайшая клетка
            point = mouse.world_point
            return (round(point.x), 0, round(point.z))
        return None

    def update(self):
        removing = held_keys["shift"] and not self.answered
        hovered = self._hovered_block()
        if not self.answered:
            for block in self.blocks.values():
                remove_me = removing and block is hovered
                block.set_color(REMOVE_HINT_COLOR if remove_me else self.accent)

        cell = None if (removing or self.answered) else self._target_cell()
        if cell is not None and self.build.can_add(cell):
            self.ghost.position = cell
            self.ghost.enabled = True
        else:
            self.ghost.enabled = False

        if self.preview:
            self.preview.rotation_y += 25 * time.dt

    def input(self, key):
        if key in LEVEL_KEYS:
            self.session = self._new_session(LEVEL_KEYS[key])  # заново
            self.new_task()
        elif key == "z" and held_keys["control"]:     # Ctrl+Z
            self.undo()
        elif key == "left mouse down" and not self.answered:
            if held_keys["shift"]:
                block = self._hovered_block()
                if block is not None:
                    self.build.remove(block.cell)
            else:
                cell = self._target_cell()
                if cell is not None:
                    self.build.add(cell)
            self._sync_blocks()

    def undo(self):
        if not self.answered and self.build.undo():
            self._sync_blocks()

    def clear(self):
        if not self.answered:
            self.build.clear()
            self._sync_blocks()

    # ---------- проверка ----------
    def check_or_next(self):
        if self.answered:
            self.next_task()
        else:
            self.check()

    def check(self):
        if not self.build.cells:
            self.feedback.text = textwrap.fill("Сначала поставьте хотя бы один кубик.", 34)
            self.feedback.color = color.hex(settings.TEXT_MUTED)
            return
        self.answered = True
        seconds = perf_counter() - self.task_started
        correct = check_build(self.build.cells, self.task.target)
        points = self.session.record(correct, seconds)

        result_color = settings.CORRECT_COLOR if correct else settings.WRONG_COLOR
        for block in self.blocks.values():
            block.set_color(result_color)
        if correct:
            message = f"Верно! Фигура совпадает.  +{points} баллов"
        else:
            message = "Не совпадает. " + build_hint(self.build.cells, self.task.target)
        # Длинную фразу переносим на несколько строк, чтобы влезла в панель
        self.feedback.text = textwrap.fill(message, 34)
        self.feedback.color = color.hex(result_color)
        self.ghost.enabled = False
        self.action_button.text = ("Результаты" if self.session.is_finished
                                   else "Дальше")
        self._refresh()

    def next_task(self):
        if self.session.is_finished:
            self.navigate("results", session=self.session)
        else:
            self.new_task()

    # ---------- выход ----------
    def go_back(self):
        self.navigate("menu")

    def close(self):
        for block in self.blocks.values():
            dispose(block)
        self.blocks = {}
        if self.preview:
            dispose(self.preview)
            self.preview = None
        super().close()
