"""3D-развёртка куба, которая умеет складываться в куб (анимация).

Клетки соединены «шарнирами» по общим рёбрам, как бумажная развёртка:
дерево с корнем в одной клетке. Сложить = повернуть каждый шарнир на 90°.
Сгибаем ВНИЗ (от зрителя), поэтому буквы оказываются снаружи куба.
"""

from collections import deque

from ursina import *
from ursina.shaders import unlit_shader

from core import settings

DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


class NetFold(Entity):
    """cells - клетки (столбец, строка); letters - буква на каждой клетке;
    marked - номер клетки, которую подсветить (или None)."""

    def __init__(self, cells, letters, marked=None, accent=None, cell=1.2, **kwargs):
        super().__init__(**kwargs)
        accent = accent or settings.ACCENT
        cells = list(cells)
        self.cell = cell
        self.hinges = []           # (шарнир, имя поворота, угол «сложено»)

        # Корень - клетка с наибольшим числом соседей: так складывание красивее
        def neighbours(c):
            return [(c[0] + dc, c[1] + dr) for dc, dr in DIRECTIONS
                    if (c[0] + dc, c[1] + dr) in cells]
        root = max(cells, key=lambda c: len(neighbours(c)))

        center_c = (min(c for c, _ in cells) + max(c for c, _ in cells)) / 2
        center_r = (min(r for _, r in cells) + max(r for _, r in cells)) / 2
        frames = {root: Entity(parent=self,
                               position=((root[0] - center_c) * cell, 0,
                                         (root[1] - center_r) * cell))}
        queue = deque([root])
        while queue:
            parent = queue.popleft()
            for child in neighbours(parent):
                if child in frames:
                    continue
                dc, dr = child[0] - parent[0], child[1] - parent[1]
                hinge = Entity(parent=frames[parent], position=(dc * cell / 2, 0, dr * cell / 2))
                frames[child] = Entity(parent=hinge, position=(dc * cell / 2, 0, dr * cell / 2))
                axis = "rotation_z" if dc else "rotation_x"
                self.hinges.append((hinge, axis, self._downward_angle(hinge, axis, frames[child])))
                queue.append(child)

        for i, (c, letter) in enumerate(zip(cells, letters)):
            frame = frames[c]
            fill = accent if i == marked else settings.NAV_FACE
            Entity(parent=frame, model="quad", rotation_x=90, scale=cell * 0.95,
                   color=color.hex(fill), shader=unlit_shader, double_sided=True)
            Text(letter, parent=frame, rotation_x=90, position=(0, 0.012, 0), origin=(0, 0),
                 scale=26 * cell / 1.2,
                 color=color.hex("#0b1220" if i == marked else settings.TEXT_STRONG))

    @staticmethod
    def _downward_angle(hinge, axis, child):
        """Угол сгиба, при котором клетка уходит ВНИЗ. Знак не угадываем,
        а проверяем: пробуем +90 и смотрим, куда сдвинулась клетка."""
        setattr(hinge, axis, 90)
        down = child.world_y < hinge.world_y
        setattr(hinge, axis, 0)
        return 90 if down else -90

    def fold(self, duration=0.9):
        """Сложить в куб (плавно)."""
        for hinge, axis, angle in self.hinges:
            hinge.animate(axis, angle, duration=duration, curve=curve.in_out_cubic)

    def unfold(self):
        for hinge, axis, _ in self.hinges:
            setattr(hinge, axis, 0)

    @property
    def is_folded(self):
        return all(abs(getattr(h, axis) - angle) < 0.5 for h, axis, angle in self.hinges)
