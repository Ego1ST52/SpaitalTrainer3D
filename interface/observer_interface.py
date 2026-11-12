"""Режим «Взгляд наблюдателя»: что видит человечек у края стола?
После ответа стол поворачивается, и вы видите башенки его глазами."""

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from interface.choice_screen import LETTERS, ChoiceGameScreen
from interface.ui_kit import FRONT
from logic.observer import ObserverTaskGenerator

SCENE_POSITION = Vec3(-1.6, -1.0, 0)
TABLE = 5.6                   # размер стола (клетки от -2 до 2)
TOWER_UNIT = 0.55             # высота одного «этажа» башенки
OBSERVER_DISTANCE = 3.7
# Поворот стола, при котором наблюдатель оказывается на месте зрителя.
# Проверено: rotation_y = 90 переносит точку справа (+x) к зрителю (-z).
TURN_TO_VIEWER = {"front": 0, "right": 90, "back": 180, "left": -90}
SIDE_POSITIONS = {"front": Vec3(0, 0, -1), "right": Vec3(1, 0, 0), "back": Vec3(0, 0, 1),
                  "left": Vec3(-1, 0, 0)}
TURN_SECONDS = 1.2


class ObserverGameScreen(ChoiceGameScreen):
    MODE = "observer"
    HINT = "Представьте, что вы встали на место человечка и смотрите на стол"
    CARD_W = 0.22
    CARD_H = 0.17
    COLUMNS = 2

    def make_generator(self, seed):
        return ObserverTaskGenerator(seed=seed)

    def build_scene(self):
        self.scene = Entity(position=SCENE_POSITION)
        Entity(parent=self.scene, model="cube", scale=(TABLE, 0.2, TABLE), y=-0.1,
               color=color.hex(settings.SURFACE_HOVER))
        Entity(parent=self.scene, model=Grid(5, 5), rotation_x=90, scale=TABLE * 5 / 5.6,
               y=0.005, color=color.hex(settings.BORDER), shader=unlit_shader)
        for tower in self.task.towers:
            block = Entity(parent=self.scene, model="cube", color=color.hex(tower.color),
                           position=(tower.x, tower.height * TOWER_UNIT / 2, tower.z),
                           scale=(0.7, tower.height * TOWER_UNIT, 0.7))
            block.tower_color = tower.color          # для проверки в тестах
        self._observer(self.task.side)
        self.task_objects.append(self.scene)

    def _observer(self, side):
        """Человечек у края стола, лицом к центру."""
        position = SIDE_POSITIONS[side] * OBSERVER_DISTANCE
        figure = Entity(parent=self.scene, position=position)
        self.figure = figure
        figure.rotation_y = {"front": 0, "right": -90, "back": 180, "left": 90}[side]
        tint = color.hex(self.accent)
        # Туловище - вытянутая сфера (готовый Cylinder из Ursina оставляет после
        # себя служебные объекты, а здесь фигура создаётся в каждом задании)
        Entity(parent=figure, model="sphere", y=0.45, scale=(0.6, 1.0, 0.6), color=tint)
        Entity(parent=figure, model="sphere", y=1.25, scale=0.55, color=tint)
        # Глаза смотрят на стол - видно, куда он повернулся
        for dx in (-0.1, 0.1):
            Entity(parent=figure, model="sphere", position=(dx, 1.3, 0.25), scale=0.1,
                   color=color.hex("#0f172a"), shader=unlit_shader)
        Text("?", parent=figure, position=(0, 1.95, 0), billboard=True, origin=(0, 0),
             scale=11, color=tint)

    def subtitle_text(self):
        return "Башенки слева направо - так, как их видит человечек"

    def draw_option(self, index, option, card):
        """Башенки на картинке: цвет и высота, слева направо."""
        width = self.CARD_W * 0.7 / len(option)
        bottom = -self.CARD_H / 2 + 0.03
        for i, (hex_color, height) in enumerate(option):
            x = (i - (len(option) - 1) / 2) * width
            Entity(parent=card, model="quad", shader=unlit_shader, origin=(0, -0.5),
                   position=(x, bottom, FRONT), scale=(width * 0.75, 0.032 * height),
                   color=color.hex(hex_color))
        Entity(parent=card, model="quad", shader=unlit_shader, position=(0, bottom - 0.004, FRONT),
               scale=(self.CARD_W * 0.8, 0.004), color=color.hex(settings.TEXT_MUTED))

    def answer_text(self):
        reason = self.task.explain(self._chosen)
        return f"Ответ {LETTERS[self.task.correct_index]}. {reason or ''}".strip()

    def choose(self, index):
        self._chosen = index
        super().choose(index)

    def after_answer(self, correct):
        # Поворачиваем стол: человечек встаёт на ваше место (сам он прячется,
        # иначе загородил бы башенки)
        self.figure.enabled = False
        self.scene.animate("rotation_y", TURN_TO_VIEWER[self.task.side],
                           duration=TURN_SECONDS, curve=curve.in_out_cubic)
