"""Режим «Сколько кубиков?»: сосчитать все кубики, включая невидимые."""

from ursina import *

from engine.objects import ShadedBlock
from interface.choice_screen import ChoiceGameScreen
from logic.counting import CountTaskGenerator

TOWER_POSITION = Vec3(0, -1.6, 0)
# Поворот башни: видны верх, перед и левый бок (так считает logic/counting.py;
# это проверяет автотест test_count_camera_sees_top_front_left)
TOWER_YAW = -35
# Камера: (положение относительно точки вращения, наклон вниз), см. main.py
CAMERA_VIEW = ((2.8, 0, -22), 28)


class CountGameScreen(ChoiceGameScreen):
    MODE = "count"
    HINT = "Камеру вращать нельзя - иначе было бы слишком просто"
    CARD_W = 0.16
    CARD_H = 0.16
    COLUMNS = 4

    def make_generator(self, seed):
        return CountTaskGenerator(seed=seed)

    def build_scene(self):
        heights = self.task.heights
        size = len(heights)
        self.tower = Entity(position=TOWER_POSITION, rotation_y=TOWER_YAW)
        self.blocks = []
        for z, row in enumerate(heights):
            for x, height in enumerate(row):
                for y in range(height):
                    block = ShadedBlock(self.accent, parent=self.tower,
                                        position=(x - (size - 1) / 2, y + 0.5, z - (size - 1) / 2))
                    self.blocks.append(block)
        self.task_objects.append(self.tower)

    def subtitle_text(self):
        return "Считайте и те кубики, которых не видно за другими"

    def option_text(self, index, option):
        return str(option)

    def answer_text(self):
        return f"Всего кубиков: {self.task.correct_option}"

    def after_answer(self, correct):
        # Башня «разлетается»: становятся видны все кубики, даже спрятанные
        for block in self.blocks:
            target = Vec3(block.x * 1.7, block.y * 1.55, block.z * 1.7)
            block.animate_position(target, duration=0.7, curve=curve.out_cubic)
