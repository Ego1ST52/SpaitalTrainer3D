import textwrap
from time import perf_counter

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.objects import AxisGizmo, ColoredCube, dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import label, Panel, TopBar, UIButton
from core.preferences import prefs
from logic.cube_skins import (face_color, face_names, has_pips, option_text,
                              start_description)
from logic.task_generator import RotationTaskGenerator
from logic.answer_checker import check_answer
from interface.game_common import LEVEL_KEYS, finish_label, finish_training, new_training
from interface.hint_control import HintMixin



# Правая панель с заданием
PANEL_X = 0.62
PANEL_WIDTH = 0.44
PANEL_LEFT = PANEL_X - PANEL_WIDTH / 2 + 0.03
PANEL_RIGHT = PANEL_X + PANEL_WIDTH / 2 - 0.03


def make_floor():
    """Пол - только полупрозрачная сетка, без сплошной заливки: так он мягко
    уходит в фоновое свечение и не обрывается резкой линией горизонта.
    Без освещения (unlit), чтобы цвет линий был ровно таким, как задан."""
    accent = color.hex(settings.ACCENT)
    floor = Entity(y=-0.85)
    Entity(parent=floor, model=Grid(30, 30), rotation_x=90, scale=30,
           color=color.rgba(accent.r, accent.g, accent.b, 0.14), shader=unlit_shader)
    return floor


class RotationGameScreen(HintMixin, BaseScreen):
    """Игровой экран режима 1: вращение куба."""

    def __init__(self, manager, level="easy", seed=None, locked=False, playlist=None):
        super().__init__(manager)
        # Вид граней из настроек игрока: от него зависят и варианты ответа
        self.skin = prefs.get("cube_skin")
        names = face_names(self.skin)
        # Цветные квадратики на кнопках ответа (у кости все грани белые - не нужны)
        self.name_to_hex = ({} if has_pips(self.skin) else
                            {name: face_color(self.skin, face) for face, name in names.items()})
        self._start(level, seed, locked, playlist)
        self.task = None
        self.task_started = 0.0
        self.answered = False
        self.playing = False       # True, пока куб показывает решение
        self.task_objects = []     # то, что пересоздаётся для каждого задания
        self.option_buttons = []

        self.own(make_floor())
        self.cube = self.own(ColoredCube(skin=self.skin, marks=prefs.get("face_marks"),
                                         scale=1.6))   # в центре: вокруг него вращается камера
        # Оси рядом с кубом: видно, что значит «вокруг оси X»
        self.own(AxisGizmo(position=(-2.5, -0.84, 0.4)))
        self.manual_moves = []     # повороты, которые игрок сделал сам
        self.drag_start = None

        self.top_bar = self.own(TopBar("rotation", self.go_back))

        left = window.top_left.x + 0.05
        self.own(label("Исходное положение", (left, 0.33), 0.8, "muted"))
        self.own(label(start_description(self.skin), (left, 0.295), 1.0))
        self.own(label("Правая кнопка мыши - осмотреть куб, колесо - приблизить",
                       (left, -0.455), 0.8, "muted"))
        self._build_manual_controls(left)

        self.own(Panel(PANEL_WIDTH, 0.78, position=(PANEL_X, -0.06)))
        self.own(label("Повороты по порядку", (PANEL_LEFT, 0.29), 0.8, "muted"))
        self.setup_hint((PANEL_RIGHT - 0.075, 0.29), scale=(0.15, 0.04), text_size=0.65)
        self.question = self.own(label("", (PANEL_LEFT, 0.02), 1.05, "strong"))
        # Разбор ошибки: почему выбранный вариант неверен
        self.explanation_title = self.own(label("", (left, 0.225), 0.8, "wrong"))
        self.explanation = self.own(label("", (left, 0.205), 0.85, "text", origin=(-0.5, 0.5)))
        self.feedback = self.own(label("", (PANEL_LEFT, -0.365), 0.95))

        self.own(UIButton("Показать решение", self.show_solution,
                          position=(PANEL_X - 0.105, -0.415), scale=(0.19, 0.055),
                          text_size=0.75))
        self.next_button = self.own(UIButton("Дальше", self.next_task,
                                             position=(PANEL_X + 0.105, -0.415),
                                             scale=(0.19, 0.055), variant="primary",
                                             text_size=0.8))
        self.new_task()

    def _start(self, level, seed=None, locked=False, playlist=None):
        """Новая тренировка: свой код и генератор заданий с этим зерном."""
        self.playlist = playlist     # шаг «Моей тренировки» или None
        self.session, seed = new_training("rotation", level, seed, locked, playlist)
        self.generator = RotationTaskGenerator(seed=seed, face_names=face_names(self.skin))

    # ---------- задания ----------
    def _clear_task_objects(self):
        for obj in self.task_objects + self.option_buttons:
            dispose(obj)
        self.task_objects = []
        self.option_buttons = []

    def new_task(self):
        self.task = self.generator.generate(self.session.current_level)
        self.answered = False
        self.task_started = perf_counter()
        self.cube.reset()
        self.manual_moves = []
        self.next_button.text = "Дальше"
        self._clear_task_objects()

        for number, (axis, angle) in enumerate(self.task.moves, start=1):
            y = 0.245 - (number - 1) * 0.042
            self.task_objects.append(
                label(f"{number}.   вокруг оси {axis.upper()}", (PANEL_LEFT, y), 1.0))
            self.task_objects.append(
                label(f"{angle:+d}°", (PANEL_RIGHT, y), 1.0, "accent", origin=(0.5, 0)))

        for index, name in enumerate(self.task.options):
            button = UIButton(option_text(self.skin, name), lambda i=index: self.choose(i),
                              position=(PANEL_X, -0.045 - index * 0.066),
                              scale=(PANEL_WIDTH - 0.06, 0.056),
                              swatch=self.name_to_hex.get(name))
            self.option_buttons.append(button)

        self.question.text = f"Какая грань окажется {self.task.target_word}?"
        self.feedback.text = ""
        self.explanation.text = ""
        self.explanation_title.text = ""
        self.reset_hint()
        self._update_status()

    def next_task(self):
        if self.playing or self.cube.busy or not self.answered:
            return              # ждём, пока куб закончит поворот
        if self.session.is_finished:
            finish_training(self)
        else:
            self.new_task()

    # ---------- ответ ----------
    def choose(self, index):
        if self.answered or self.playing or self.hint_blocked(index):
            return
        self.answered = True
        self.close_hint()
        seconds = perf_counter() - self.task_started
        correct = check_answer(self.task, index)
        points = self.session.record(correct, seconds,
                                     self.task.tags + self.task.answer_tags(index),
                                     hints=self.hints_used)
        self.top_bar.flash_level(self.session)   # «Уровень повышен» и т.п.

        self.option_buttons[self.task.correct_index].set_variant("correct")
        if correct:
            self.feedback.text = f"Верно!  +{points} баллов"
            self.feedback.color = color.hex(settings.CORRECT_COLOR)
        else:
            self.option_buttons[index].set_variant("wrong")
            self.feedback.text = f"Неверно. Ответ: {option_text(self.skin, self.task.correct_option).lower()}"
            self.feedback.color = color.hex(settings.WRONG_COLOR)
            reason = self.task.explain(index)
            if reason:
                self.explanation_title.text = "Разбор ошибки"
                self.explanation.text = textwrap.fill(
                    reason + " Нажмите «Показать решение», чтобы увидеть повороты.", 46)
        if self.session.is_finished:
            self.next_button.text = finish_label(self)
        self._update_status()

    # ---------- ручное вращение куба ----------
    def _build_manual_controls(self, left):
        """Кнопки «X+ X- Y+ Y- Z+ Z-» и «Сброс»: игрок сам крутит куб.
        Клавиши X, Y, Z (с Shift - обратно), R - сброс; можно и тянуть мышью."""
        self.manual_title = self.own(label("", (left, -0.3), 0.8, "muted"))
        self.manual_log = self.own(label("", (left, -0.405), 0.8, "accent"))
        x = left + 0.03
        for axis in "xyz":
            for sign in (1, -1):
                text = f"{axis.upper()}{'+' if sign > 0 else '-'}"
                self.own(UIButton(text, lambda a=axis, s=sign: self.manual_turn(a, s),
                                  position=(x, -0.35), scale=(0.055, 0.045), text_size=0.75))
                x += 0.06
        self.own(UIButton("Сброс", self.manual_reset, position=(x + 0.03, -0.35),
                          scale=(0.1, 0.045), text_size=0.75, variant="ghost"))

    def can_rotate_manually(self):
        """До ответа крутить нельзя (иначе ответ можно просто подсмотреть),
        если в настройках не включена подсказка «вращать куб до ответа»."""
        allowed = self.answered or prefs.get("free_rotation")
        return allowed and not self.playing and not self.cube.busy

    def manual_turn(self, axis, sign):
        if not self.can_rotate_manually():
            return False
        self.cube.rotate_world(axis, 90 * sign)
        self.manual_moves.append(f"{axis.upper()}{'+' if sign > 0 else '-'}")
        self._update_manual_text()
        return True

    def manual_reset(self):
        if not self.can_rotate_manually():
            return
        self.cube.reset()
        self.manual_moves = []
        self._update_manual_text()

    def _update_manual_text(self):
        if self.can_rotate_manually() or self.manual_moves:
            self.manual_title.text = ("Покрутите куб сами: X, Y, Z (Shift - обратно), "
                                      "мышь - перетащить, R - сброс")
        else:
            self.manual_title.text = "Покрутить куб самому можно после ответа"
        moves = "  ".join(self.manual_moves[-8:])
        self.manual_log.text = f"Ваши повороты:  {moves}" if moves else ""

    def _update_status(self):
        self.top_bar.update_state(self.session, self.answered)
        self._update_manual_text()

    # ---------- решение ----------
    def show_solution(self):
        if not self.answered or self.playing:
            return
        self.playing = True
        self.cube.reset()
        # Повороты идут цепочкой: каждый следующий - после окончания предыдущего
        self.cube.play_moves(self.task.moves, on_done=self._solution_done)

    def _solution_done(self):
        self.playing = False
        self.manual_moves = []          # после решения куб в итоговом положении задания
        self._update_manual_text()

    # ---------- выход ----------
    def go_back(self):
        if self.playing or self.cube.busy:
            return  # не уходим посреди анимации
        self.navigate("menu")

    def close(self):
        self._clear_task_objects()
        super().close()

    # ---------- клавиши ----------
    def input(self, key):
        if key in LEVEL_KEYS and not self.playing and not self.cube.busy                 and not self.session.locked:
            self._start(LEVEL_KEYS[key])  # заново, с новым кодом
            self.new_task()
        elif key in ("x", "y", "z"):
            self.manual_turn(key, -1 if held_keys["shift"] else 1)
        elif key == "r":
            self.manual_reset()
        elif key == "h":
            self.use_hint()
        elif key == "left mouse down":
            # тянуть можно, только если нажали не на кнопку интерфейса
            hovered = mouse.hovered_entity
            self.drag_start = None if isinstance(hovered, Button) else Vec2(mouse.x, mouse.y)
        elif key == "left mouse up" and self.drag_start is not None:
            delta = Vec2(mouse.x, mouse.y) - self.drag_start
            self.drag_start = None
            if max(abs(delta.x), abs(delta.y)) < 0.05:
                return
            # Потянули вправо - передняя грань уходит вправо (поворот вокруг Y),
            # вверх - передняя грань уходит вверх (поворот вокруг X)
            if abs(delta.x) > abs(delta.y):
                self.manual_turn("y", -1 if delta.x > 0 else 1)
            else:
                self.manual_turn("x", 1 if delta.y > 0 else -1)
