import textwrap
from time import perf_counter

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.objects import ShadedBlock, ShadedShape, dispose
from interface.base_screen import BaseScreen
from logic.stl import export_stl
from interface.ui_kit import label, mode_color, Panel, TopBar, UIButton
from logic.construction import Build, ConstructionTaskGenerator, GRID_HALF, \
    build_diff, build_hint, check_build
from interface.game_common import (LEVEL_KEYS, finish_label, finish_training, new_training,
                                     task_source)


PANEL_X = 0.62
PANEL_WIDTH = 0.44
PANEL_LEFT = PANEL_X - PANEL_WIDTH / 2 + 0.03
PREVIEW_Y = 0.14
PREVIEW_BOX = 0.22                 # размер образца в панели (по большей стороне)
PREVIEW_DRAG = 300                 # градусов поворота образца на ширину экрана
REMOVE_HINT_COLOR = "#f87171"      # кубик под курсором при Shift (будет удалён)


class ConstructionGameScreen(BaseScreen):
    """Режим 4: собрать из кубиков фигуру по образцу.
    Клик - поставить кубик, Shift+клик - убрать, Ctrl+Z - отменить."""

    MODE = "construction"
    SAMPLE_TITLE = "Образец"

    def __init__(self, manager, level="easy", seed=None, locked=False, playlist=None):
        super().__init__(manager)
        self.accent = mode_color(self.MODE)
        self._start(level, seed, locked, playlist)
        self.task = None
        self.build = None
        self.blocks = {}            # клетка -> 3D-кубик
        self.task_started = 0.0
        self.answered = False
        self.preview = None
        self.preview_drag = None    # положение мыши, когда начали крутить образец
        self.preview_touched = False
        self.diff_ghosts = []       # прозрачные кубики «здесь не хватает»
        self.sample_objects = []    # то, что рисует образец (кроме self.preview)

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

        self.top_bar = self.own(TopBar(self.MODE, self.go_back))
        self.own(Panel(PANEL_WIDTH, 0.78, position=(PANEL_X, -0.06)))
        self.sample_title = self.own(label(self.SAMPLE_TITLE, (PANEL_LEFT, 0.29), 0.8, "muted"))
        self.preview_hint = self.own(label("потяните мышью, чтобы покрутить",
                                           (PANEL_X + PANEL_WIDTH / 2 - 0.03, 0.29), 0.65,
                                           "muted", origin=(0.5, 0)))
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
        # После проверки постройку можно сохранить для 3D-принтера
        self.export_folder = None        # None - «Документы\SpatialTrainer3D»
        self.stl_button = self.own(UIButton("Сохранить для 3D-печати", self.save_stl,
                                            position=(PANEL_X, -0.35),
                                            scale=(PANEL_WIDTH - 0.06, 0.045), text_size=0.75))
        self.stl_button.enabled = False

        self.own(label("Клик - поставить кубик  •  Shift+клик - убрать  •  Ctrl+Z - отменить"
                       "  •  правая кнопка мыши - вращать камеру, колесо - приблизить",
                       (window.top_left.x + 0.05, -0.455), 0.75, "muted"))
        self.new_task()

    def _start(self, level, seed=None, locked=False, playlist=None):
        """Новая тренировка: свой код и генератор заданий с этим зерном."""
        self.playlist = playlist     # шаг «Моей тренировки» или None
        self.session, seed = new_training(self.MODE, level, seed, locked, playlist)
        self.generator = task_source(self.session, self.make_generator, seed)

    # ---------- задания ----------
    def new_task(self):
        self.task = self.generator.generate(self.session.current_level)
        self.build = self.make_build()
        self.answered = False
        self.task_started = perf_counter()
        for block in self.blocks.values():
            dispose(block)
        self.blocks = {}
        self._clear_diff()

        self._clear_sample()
        self.show_sample()
        self.preview_drag = None
        self.preview_touched = False
        self._sync_blocks()

        self.question.text = textwrap.fill(self.task.question, 28)
        self.feedback.text = ""
        self.action_button.text = "Проверить"
        self.stl_button.enabled = False
        self._refresh()
        self.on_task_started()

    # ---------- точки расширения (см. режимы «По памяти», «Симметрия», «По видам») ----------
    def make_generator(self, seed):
        return ConstructionTaskGenerator(seed=seed)

    def make_build(self):
        return Build(self.task.max_cubes)

    def show_sample(self):
        """Нарисовать образец в правой панели (по умолчанию - крутящаяся фигура)."""
        target = self.task.target
        extent = max(max(c[i] for c in target) - min(c[i] for c in target)
                     for i in range(3)) + 1
        self.preview = ShadedShape(target, self.accent, position=(PANEL_X, PREVIEW_Y, -0.3),
                                   scale=min(0.06, PREVIEW_BOX / extent), rotation_x=-25)

    def _clear_sample(self):
        if self.preview:
            dispose(self.preview)
            self.preview = None
        for obj in self.sample_objects:
            dispose(obj)
        self.sample_objects = []

    def block_color(self, cell):
        """Цвет кубика постройки, пока идёт сборка."""
        return self.accent

    def is_correct(self):
        return check_build(self.build.cells, self.task.target)

    def mistake_message(self):
        """Что написать после неверной проверки (и что подсветить на площадке)."""
        return build_hint(self.build.cells, self.task.target) + " " + self._show_diff()

    def diff_cells(self):
        """(совпавшие, лишние, недостающие) клетки для подсветки ошибок."""
        return build_diff(self.build.cells, self.task.target)

    def counter_text(self):
        return (f"Поставлено: {len(self.build.cells)} из "
                f"{len(self.task.target)}  (можно до {self.build.max_cubes})")

    def save_stl(self):
        """Сохранить постройку (или образец, если ничего не построено) в STL."""
        cells = sorted(self.build.cells) or list(self.task.target)
        try:
            path = export_stl(cells, self.export_folder)
        except OSError as error:
            self.counter.text = f"Не удалось сохранить: {error}"
            return None
        self.counter.text = textwrap.fill(
            f"Сохранено: Документы › {path.parent.name} › {path.name}", 40)
        return path

    def on_task_started(self):
        """Вызывается, когда показано новое задание."""

    def on_checked(self, correct):
        """Вызывается после проверки постройки."""

    def can_build(self):
        """Можно ли сейчас ставить и убирать кубики."""
        return not self.answered

    def _refresh(self):
        self.counter.text = self.counter_text()
        self.top_bar.update_state(self.session, self.answered)

    # ---------- кубики ----------
    def _sync_blocks(self):
        """Привести 3D-кубики в соответствие с постройкой (после отмены и т.п.)."""
        for cell in list(self.blocks):
            if cell not in self.build.cells:
                dispose(self.blocks.pop(cell))
        for cell in self.build.cells:
            if cell not in self.blocks:
                block = ShadedBlock(self.block_color(cell), position=cell)
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
        building = self.can_build()
        removing = held_keys["shift"] and building
        hovered = self._hovered_block()
        if building:
            for block in self.blocks.values():
                remove_me = removing and block is hovered
                block.set_color(REMOVE_HINT_COLOR if remove_me else self.block_color(block.cell))

        cell = None if (removing or not building) else self._target_cell()
        if cell is not None and self.build.can_add(cell):
            self.ghost.position = cell
            self.ghost.enabled = True
        else:
            self.ghost.enabled = False

        if self.preview:
            self.preview_hint.enabled = self.preview.enabled   # в «По памяти» образец прячут
            if self.preview_drag is not None:
                # Крутим образец мышью: влево-вправо - вокруг вертикали, вверх-вниз - наклон
                delta = Vec2(mouse.x, mouse.y) - self.preview_drag
                self.preview_drag = Vec2(mouse.x, mouse.y)
                self.preview.rotation_y -= delta.x * PREVIEW_DRAG
                self.preview.rotation_x = clamp(self.preview.rotation_x - delta.y * PREVIEW_DRAG,
                                                -80, 80)
            elif not self.preview_touched:
                self.preview.rotation_y += 25 * time.dt   # пока не трогали - вращается сам

    def _mouse_over_preview(self):
        """Курсор над образцом в правой панели."""
        try:
            x, y = mouse.x, mouse.y
        except AttributeError:          # окно без мыши (автотесты)
            return False
        return abs(x - PANEL_X) < PANEL_WIDTH / 2 - 0.02 and abs(y - PREVIEW_Y) < 0.13

    def input(self, key):
        if key in LEVEL_KEYS and not self.session.locked:
            self._start(LEVEL_KEYS[key])  # заново, с новым кодом
            self.new_task()
        elif key == "z" and held_keys["control"]:     # Ctrl+Z
            self.undo()
        elif key == "left mouse down" and self.preview and self.preview.enabled \
                and self._mouse_over_preview():
            self.preview_drag = Vec2(mouse.x, mouse.y)
            self.preview_touched = True
        elif key == "left mouse up":
            self.preview_drag = None
        elif key == "left mouse down" and self.can_build():
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
        if self.can_build() and self.build.undo():
            self._sync_blocks()

    def clear(self):
        if self.can_build():
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
        correct = self.is_correct()
        points = self.session.record(correct, seconds, self.task.tags)
        self.top_bar.flash_level(self.session)   # «Уровень повышен» и т.п.

        result_color = settings.CORRECT_COLOR if correct else settings.WRONG_COLOR
        for block in self.blocks.values():
            block.set_color(result_color)
        if correct:
            message = f"Верно! Фигура совпадает.  +{points} баллов"
        else:
            message = "Не совпадает. " + self.mistake_message()
        # Длинную фразу переносим на несколько строк, чтобы влезла в панель
        self.feedback.text = textwrap.fill(message, 34)
        self.feedback.color = color.hex(result_color)
        self.ghost.enabled = False
        self.action_button.text = (finish_label(self) if self.session.is_finished
                                   else "Дальше")
        self._refresh()
        self.stl_button.enabled = True
        self.on_checked(correct)

    def _show_diff(self):
        """Показать, чем постройка отличается от образца: совпавшие кубики -
        зелёные, лишние - красные, недостающие - прозрачные зелёные."""
        matched, extra, missing = self.diff_cells()
        for cell, block in self.blocks.items():
            block.set_color(settings.CORRECT_COLOR if cell in matched
                            else settings.WRONG_COLOR)
        good = color.hex(settings.CORRECT_COLOR)
        for cell in sorted(missing):
            self.diff_ghosts.append(Entity(model="cube", position=cell, scale=0.9,
                                           color=color.rgba(good.r, good.g, good.b, 0.55),
                                           shader=unlit_shader))
        parts = [f"Совпало {len(matched)} из {len(self.task.target)}."]
        if extra:
            parts.append("Красные - лишние.")
        if missing:
            parts.append("Прозрачные - не хватает.")
        return " ".join(parts)

    def _clear_diff(self):
        for ghost in self.diff_ghosts:
            dispose(ghost)
        self.diff_ghosts = []

    def next_task(self):
        if self.session.is_finished:
            finish_training(self)
        else:
            self.new_task()

    # ---------- выход ----------
    def go_back(self):
        self.navigate("menu")

    def close(self):
        for block in self.blocks.values():
            dispose(block)
        self.blocks = {}
        self._clear_diff()
        self._clear_sample()
        super().close()
