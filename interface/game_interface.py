from ursina import *

from core import settings
from engine.objects import ColoredCube, dispose
from interface.base_screen import BaseScreen
from logic.task_generator import RotationTaskGenerator
from logic.answer_checker import check_answer

LEVEL_NAMES = {"easy": "Начальный", "medium": "Средний", "hard": "Продвинутый"}
LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}


class RotationGameScreen(BaseScreen):
    """Игровой экран режима 1: вращение куба."""

    def __init__(self, manager, level="easy"):
        super().__init__(manager)
        self.level = level
        self.generator = RotationTaskGenerator()
        self.task = None
        self.answered = False
        self.playing = False       # True, пока куб показывает решение
        self.correct_count = 0
        self.total = 0
        self.option_buttons = []

        self.own(Entity(model="plane", scale=14, y=-1.5,
                        color=color.hex(settings.FLOOR_COLOR)))
        self.cube = self.own(ColoredCube())

        text_color = color.hex(settings.TEXT_COLOR)
        self.title = self.own(Text("", position=window.top_left + Vec2(0.03, -0.03),
                                   color=color.hex(settings.ACCENT), scale=1.4))
        self.question = self.own(Text("", position=window.top_left + Vec2(0.03, -0.1),
                                      color=text_color, scale=1.1))
        self.feedback = self.own(Text("", position=(0.35, -0.2),
                                      color=color.hex(settings.ACCENT), scale=1.2))
        self.score = self.own(Text("", position=window.bottom_left + Vec2(0.03, 0.08),
                                   color=text_color, scale=1.1))

        self.own(self._make_button("Показать решение", (0.55, -0.32), self.show_solution))
        self.own(self._make_button("Следующее задание", (0.55, -0.41), self.next_task))
        self.own(self._make_button("В меню", (0.75, 0.43), self.go_back,
                                   scale=(0.22, 0.06)))
        self.new_task()

    def _make_button(self, label, position, action, scale=(0.4, 0.07)):
        button = Button(text=label, color=color.hex(settings.BUTTON_COLOR),
                        highlight_color=color.hex(settings.BUTTON_HOVER),
                        scale=scale, position=position)
        button.on_click = action
        return button

    # ---------- задания ----------
    def new_task(self):
        self.task = self.generator.generate(self.level)
        self.answered = False
        self.cube.reset()

        for button in self.option_buttons:
            dispose(button)
        self.option_buttons = []
        for index, name in enumerate(self.task.options):
            button = self._make_button(name.capitalize(), (0.55, 0.2 - index * 0.09),
                                       lambda i=index: self.choose(i))
            self.option_buttons.append(button)

        lines = ["Сейчас сверху белая грань, спереди зелёная.",
                 "Повороты по порядку:"]
        for number, (axis, angle) in enumerate(self.task.moves, start=1):
            lines.append(f"  {number}) вокруг оси {axis.upper()} на {angle:+d}°")
        lines.append("Какая грань окажется сверху?")
        self.question.text = "\n".join(lines)

        self.title.text = f"Вращение. Уровень: {LEVEL_NAMES[self.level]}"
        self.feedback.text = ""
        self._update_score()

    def next_task(self):
        if self.playing:
            return
        self.new_task()

    # ---------- ответ ----------
    def choose(self, index):
        if self.answered or self.playing:
            return
        self.answered = True
        self.total += 1
        if check_answer(self.task, index):
            self.correct_count += 1
            self.feedback.text = "Верно!"
        else:
            self.feedback.text = ("Неверно. Правильный ответ: "
                                  f"{self.task.correct_option}")
        self._update_score()

    def _update_score(self):
        hint = "Уровень: клавиши 1, 2, 3"
        if self.total:
            percent = round(100 * self.correct_count / self.total)
            self.score.text = (f"Верно: {self.correct_count} из {self.total} "
                               f"({percent}%)   {hint}")
        else:
            self.score.text = hint

    # ---------- решение ----------
    def show_solution(self):
        if not self.answered or self.playing:
            return
        self.playing = True
        self.cube.reset()
        step = settings.ROTATION_DURATION + 0.15
        for number, (axis, angle) in enumerate(self.task.moves):
            invoke(self.cube.rotate_world, axis, angle, delay=number * step)
        invoke(self._solution_done, delay=len(self.task.moves) * step)

    def _solution_done(self):
        self.playing = False

    # ---------- выход ----------
    def go_back(self):
        if self.playing or self.cube.busy:
            return  # не уходим посреди анимации
        self.navigate("menu")

    def close(self):
        for button in self.option_buttons:
            dispose(button)
        self.option_buttons = []
        super().close()

    # ---------- клавиши ----------
    def input(self, key):
        if key in LEVEL_KEYS and not self.playing:
            self.level = LEVEL_KEYS[key]
            self.new_task()