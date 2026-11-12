"""Демо-режим для выступления: тренажёр сам показывает режимы по очереди.

В каждом режиме: открыть задание, подождать, ответить правильно (или собрать
фигуру по кубику), показать решение - и дальше. Тренировки в демо не
заканчиваются, поэтому в статистику ничего не попадает.
Esc - выйти в меню. Если игрок сам ушёл с экрана, демо тихо останавливается.
"""

from ursina import *

from engine.objects import dispose
from interface import ui_kit
from interface.base_screen import BaseScreen
from interface.ui_kit import label, Panel
from logic.construction import Build
from logic.symmetry import mirrored_part

# (режим, сколько секунд показывать после ответа)
DEMO_STEPS = [("rotation", 4.5), ("matching", 4.5), ("projection", 3.5),
              ("construction", 3.0), ("reverse", 3.5), ("views", 3.0), ("symmetry", 3.0),
              ("nets", 4.0), ("shadow", 3.0)]
THINK_SECONDS = 2.2        # «подумать» перед ответом
CUBE_SECONDS = 0.3         # пауза между кубиками при сборке


class DemoStartScreen(BaseScreen):
    """Заставка на мгновение, пока демо открывает первый режим."""

    def __init__(self, manager):
        super().__init__(manager)
        self.own(label("Демо-режим", (0, 0.03), 2.2, "strong", origin=(0, 0)))
        self.own(label("Esc - выйти", (0, -0.04), 0.9, "muted", origin=(0, 0)))


def build_order(cells, can_add):
    """Порядок кубиков для сборки: каждый следующий можно поставить (стоит на
    полу или касается уже поставленных). can_add(клетка, поставленные) -> bool."""
    left, placed, order = list(cells), set(), []
    while left:
        for cell in left:
            if can_add(cell, placed):
                order.append(cell)
                placed.add(cell)
                left.remove(cell)
                break
        else:
            break                       # больше ничего не ставится
    return order


def demo_cells(screen):
    """Какие кубики поставить, чтобы ответ в режиме-стройке был верным."""
    task = screen.task
    if screen.MODE == "symmetry":
        return sorted(mirrored_part(task.given, task.plane))
    shape = getattr(task, "shape", None) or task.target
    return sorted((x - 1, y, z - 1) for x, y, z in shape)


class DemoDirector(Entity):
    def __init__(self, manager, steps=None):
        super().__init__()
        self.manager = manager
        self.steps = list(steps or DEMO_STEPS)
        self.index = -1
        self.screen = None
        self.stopped = False
        ui_kit.SUPPRESS_TUTORIALS = True     # в демо подсказки не всплывают
        self.banner = Panel(0.36, 0.045, position=(0, 0.355))
        self.banner_text = label("", (0, 0.355), 0.8, "accent", origin=(0, 0))
        invoke(self.next_mode, delay=0.4)

    # ---------- ход демо ----------
    def _alive(self):
        """Демо продолжается, только пока на экране тот режим, который оно открыло."""
        return not self.stopped and self.screen is not None and \
            self.manager.current is self.screen

    def next_mode(self):
        if self.stopped:
            return
        self.index += 1
        if self.index >= len(self.steps):
            self.stop(to_menu=True)
            return
        mode, _ = self.steps[self.index]
        self.manager.go(mode, level="easy")
        self.screen = self.manager.current
        self.banner_text.text = f"Демо {self.index + 1} из {len(self.steps)}  •  Esc - выход"
        invoke(self.answer, delay=THINK_SECONDS)

    def answer(self):
        if not self._alive():
            return self.stop()
        screen = self.screen
        if hasattr(screen, "build"):
            order = build_order(demo_cells(screen),
                                lambda cell, placed: self._can_add(screen, cell, placed))
            self._place(order)
            return
        screen.choose(screen.task.correct_index)
        for method in ("show_solution", "look_from_view"):
            if hasattr(screen, method):
                invoke(self._call, method, delay=0.7)
                break
        invoke(self.next_mode_if_alive, delay=self.steps[self.index][1])

    @staticmethod
    def _can_add(screen, cell, placed):
        """Можно ли поставить кубик, если уже стоят placed (плюс то, что на
        площадке сейчас, - например, данные кубики «Симметрии»)."""
        probe = Build(screen.build.max_cubes)
        probe.cells = set(screen.build.cells) | set(placed)
        return probe.can_add(cell)

    def _place(self, order):
        """Ставить кубики по одному, потом проверить."""
        if not self._alive():
            return self.stop()
        screen = self.screen
        if order:
            screen.build.add(order[0])
            screen._sync_blocks()
            invoke(self._place, order[1:], delay=CUBE_SECONDS)
            return
        screen.check()
        invoke(self.next_mode_if_alive, delay=self.steps[self.index][1])

    def _call(self, method):
        if self._alive():
            getattr(self.screen, method)()

    def next_mode_if_alive(self):
        if not self._alive():
            return self.stop()
        if getattr(self.screen, "playing", False) or getattr(getattr(self.screen, "cube", None),
                                                             "busy", False):
            invoke(self.next_mode_if_alive, delay=0.3)      # ждём конца анимации
            return
        self.next_mode()

    # ---------- выход ----------
    def input(self, key):
        if key == "escape" and not self.stopped:
            self.stop(to_menu=True)

    def stop(self, to_menu=False):
        if self.stopped:
            return
        self.stopped = True
        ui_kit.SUPPRESS_TUTORIALS = False
        dispose(self.banner)
        dispose(self.banner_text)
        if to_menu:
            invoke(self.manager.go, "menu", delay=0.05)
        # Сам «режиссёр» удаляется сразу; отложенные вызовы, которые ещё ждут,
        # увидят stopped=True и ничего не сделают
        destroy(self)
