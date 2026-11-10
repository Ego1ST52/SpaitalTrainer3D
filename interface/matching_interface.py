from ursina import *

from core import settings
from engine.objects import ShapeView, dispose
from interface.base_screen import BaseScreen
from logic.matching_tasks import MatchingTaskGenerator
from logic.answer_checker import check_answer

LEVEL_NAMES = {"easy": "Начальный", "medium": "Средний", "hard": "Продвинутый"}
LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}
LETTERS = "АБВГД"
SPACING = 4.2   # расстояние между вариантами в сцене


class MatchingGameScreen(BaseScreen):
    """Игровой экран режима 2: найти фигуру, совпадающую с образцом."""

    def __init__(self, manager, level="easy"):
        super().__init__(manager)
        self.level = level
        self.generator = MatchingTaskGenerator()
        self.task = None
        self.answered = False
        self.correct_count = 0
        self.total = 0
        self.scene_objects = []   # 3D-объекты текущего задания
        self.option_views = []
        self.option_buttons = []

        text_color = color.hex(settings.TEXT_COLOR)
        self.title = self.own(Text("", position=window.top_left + Vec2(0.03, -0.03),
                                   color=color.hex(settings.ACCENT), scale=1.4))
        self.question = self.own(Text("", position=window.top_left + Vec2(0.03, -0.1),
                                      color=text_color, scale=1.1))
        self.feedback = self.own(Text("", position=(-0.2, -0.3),
                                      color=color.hex(settings.ACCENT), scale=1.3))
        self.score = self.own(Text("", position=window.bottom_left + Vec2(0.03, 0.06),
                                   color=text_color, scale=1.1))

        self.own(self._make_button("Следующее задание", (0.62, -0.4), self.new_task,
                                   scale=(0.3, 0.07)))
        self.own(self._make_button("В меню", (0.75, 0.43), self.go_back,
                                   scale=(0.22, 0.06)))
        self.new_task()

    def _make_button(self, label, position, action, scale):
        button = Button(text=label, color=color.hex(settings.BUTTON_COLOR),
                        highlight_color=color.hex(settings.BUTTON_HOVER),
                        scale=scale, position=position)
        button.on_click = action
        return button

    def _label(self, text, position):
        label = Text(text, parent=scene, position=position, billboard=True,
                     scale=settings.LABEL_SCALE, origin=(0, 0),
                     color=color.hex(settings.TEXT_COLOR))
        self.scene_objects.append(label)

    def _clear_task_objects(self):
        for obj in self.scene_objects + self.option_buttons:
            dispose(obj)
        self.scene_objects = []
        self.option_views = []
        self.option_buttons = []

    def new_task(self):
        self.task = self.generator.generate(self.level)
        self.answered = False
        self._clear_task_objects()

        reference = ShapeView(self.task.reference, settings.SHAPE_COLOR,
                              position=(0, 3.2, 0))
        self.scene_objects.append(reference)
        self._label("Образец", (0, 5.6, 0))

        count = len(self.task.options)
        for index, cells in enumerate(self.task.options):
            x = (index - (count - 1) / 2) * SPACING
            view = ShapeView(cells, settings.SHAPE_COLOR, position=(x, -2.2, 0))
            self.scene_objects.append(view)
            self.option_views.append(view)
            self._label(LETTERS[index], (x, -0.2, 0))

            button = self._make_button(
                LETTERS[index], ((index - (count - 1) / 2) * 0.18, -0.4),
                lambda i=index: self.choose(i), scale=(0.15, 0.07))
            self.option_buttons.append(button)

        self.title.text = f"Одинаковые фигуры. Уровень: {LEVEL_NAMES[self.level]}"
        self.question.text = self.task.question
        self.feedback.text = ""
        self._update_score()

    def choose(self, index):
        if self.answered:
            return
        self.answered = True
        self.total += 1
        is_correct = check_answer(self.task, index)

        self.option_views[self.task.correct_index].set_color(settings.CORRECT_COLOR)
        if is_correct:
            self.correct_count += 1
            self.feedback.text = "Верно!"
        else:
            self.option_views[index].set_color(settings.WRONG_COLOR)
            self.feedback.text = ("Неверно. Правильный ответ: "
                                  f"{LETTERS[self.task.correct_index]}")
        self._update_score()

    def _update_score(self):
        hint = "Уровень: клавиши 1, 2, 3"
        if self.total:
            percent = round(100 * self.correct_count / self.total)
            self.score.text = (f"Верно: {self.correct_count} из {self.total} "
                               f"({percent}%)   {hint}")
        else:
            self.score.text = hint

    def go_back(self):
        self.navigate("menu")

    def close(self):
        self._clear_task_objects()
        super().close()

    def input(self, key):
        if key in LEVEL_KEYS:
            self.level = LEVEL_KEYS[key]
            self.new_task()