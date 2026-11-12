import random

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from engine.backdrop import FloatingCubes
from interface.base_screen import BaseScreen
from interface.ui_kit import FRONT, label, mode_color, Panel, Segmented, UIButton
from logic.playlist import MODE_ORDER, Playlist, build_steps, validate_plan

SHORT_NAMES = {"rotation": "Вращение", "matching": "Фигуры", "projection": "Проекции",
               "construction": "Сборка", "nets": "Развёртка", "sections": "Сечения",
               "count": "Кубики", "memory": "Память", "shadow": "Тень"}
# Примерно секунд на одно задание - для оценки длительности
SECONDS_PER_TASK = {"rotation": 15, "matching": 20, "projection": 20, "construction": 60,
                    "nets": 20, "sections": 25, "count": 15, "memory": 70, "shadow": 20}

LABEL_X = -0.8
CONTROL_X = -0.2
CONTROL_WIDTH = 0.66
SUMMARY_X = 0.52


def tasks_text(count):
    """3 задания, 5 заданий, 21 задание."""
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} задание"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} задания"
    return f"{count} заданий"


def minutes_text(seconds):
    minutes = max(1, round(seconds / 60))
    if minutes % 10 == 1 and minutes % 100 != 11:
        word = "минута"
    elif minutes % 10 in (2, 3, 4) and minutes % 100 not in (12, 13, 14):
        word = "минуты"
    else:
        word = "минут"
    return f"около {minutes} {word}"


class CustomTrainingScreen(BaseScreen):
    """Конструктор «Моей тренировки». plan - последний выбор игрока (словарь,
    см. logic/playlist.validate_plan); on_save(plan) запоминает новый выбор."""

    def __init__(self, manager, plan, on_save):
        super().__init__(manager)
        self.plan = dict(plan)
        self.plan["modes"] = list(plan["modes"])
        self.on_save = on_save
        self.mode_buttons = {}
        self.summary_objects = []
        self.own(FloatingCubes())

        right = window.top_right.x - 0.05
        self.own(label("Моя тренировка", (LABEL_X, 0.42), 2.0, "strong"))
        self.own(label("Соберите тренировку из нескольких режимов", (LABEL_X, 0.365),
                       0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06),
                          variant="ghost"))

        # Режимы: переключатели в три ряда, можно выбрать несколько
        y = 0.25
        self.own(label("Режимы", (LABEL_X, y), 0.9))
        pad, columns = 0.01, 3
        chip = (CONTROL_WIDTH - pad * (columns - 1)) / columns
        for i, mode in enumerate(MODE_ORDER):
            row, col = divmod(i, columns)
            x = CONTROL_X - CONTROL_WIDTH / 2 + chip / 2 + col * (chip + pad)
            button = self.own(UIButton(SHORT_NAMES[mode], lambda m=mode: self.toggle(m),
                                       position=(x, y - row * 0.072), scale=(chip, 0.062),
                                       text_size=0.75, swatch=mode_color(mode)))
            self.mode_buttons[mode] = button
        y -= 0.072 * 2

        rows = [
            ("Уровень", "level", [("easy", "Начальный"), ("medium", "Средний"),
                                  ("hard", "Продвинутый")]),
            ("Заданий на режим", "per_mode", [(3, "3"), (5, "5"), (10, "10")]),
            ("Порядок", "order", [("blocks", "Блоками"), ("mixed", "Вперемешку")]),
            ("Адаптивная сложность", "adaptive", [(False, "Выкл"), (True, "Вкл")]),
        ]
        for caption, key, options in rows:
            y -= 0.09
            self.own(label(caption, (LABEL_X, y), 0.9))
            self.own(Segmented(options, self.plan[key],
                               lambda value, k=key: self.change(k, value),
                               position=(CONTROL_X, y), width=CONTROL_WIDTH, text_size=0.8))
        self.own(label("Адаптивная: 3 верных подряд - уровень выше, 2 ошибки подряд - ниже",
                       (LABEL_X, y - 0.06), 0.75, "muted"))

        # Сводка справа
        self.own(Panel(0.6, 0.5, position=(SUMMARY_X, 0.06)))
        self.own(label("Сводка", (SUMMARY_X - 0.27, 0.27), 0.8, "muted"))
        self.error = self.own(label("", (SUMMARY_X, -0.25), 0.85, "wrong", origin=(0, 0)))
        self.start_button = self.own(UIButton("Начать тренировку", self.start,
                                              position=(SUMMARY_X, -0.31), scale=(0.6, 0.07),
                                              variant="primary"))
        self.refresh()

    # ---------- выбор ----------
    def toggle(self, mode):
        modes = self.plan["modes"]
        if mode in modes:
            modes.remove(mode)
        else:
            modes.append(mode)
        self.refresh()

    def change(self, key, value):
        self.plan[key] = value
        self.refresh()

    def refresh(self):
        for mode, button in self.mode_buttons.items():
            button.set_variant("primary" if mode in self.plan["modes"] else "ghost")
        for obj in self.summary_objects:
            destroy(obj)
        self.summary_objects = []
        self.error.text = ""

        modes = [m for m in MODE_ORDER if m in self.plan["modes"]]
        if not modes:
            self._summary_text("Выберите хотя бы один режим", (SUMMARY_X, 0.06), 1.0, "muted",
                               origin=(0, 0))
            return
        per_mode = self.plan["per_mode"]
        total = per_mode * len(modes)
        seconds = sum(SECONDS_PER_TASK[m] * per_mode for m in modes)
        left = SUMMARY_X - 0.27
        self._summary_text(tasks_text(total), (left, 0.205), 1.8, "strong")
        self._summary_text(minutes_text(seconds), (left, 0.14), 0.85, "muted")
        for i, mode in enumerate(modes):
            column, row = divmod(i, 5)                  # больше пяти - во второй столбец
            x, y = left + column * 0.27, 0.08 - row * 0.04
            self._summary_bar(x + 0.006, y, 0.012, 0.022, mode_color(mode))
            self._summary_text(f"{SHORT_NAMES[mode]}  -  {per_mode}", (x + 0.025, y),
                               0.85, "text")

        # Лента порядка: каждый прямоугольник - одно задание в цвете своего режима.
        # Для «вперемешку» это пример: настоящий порядок выпадет случайно.
        steps = build_steps(modes, per_mode, self.plan["order"], random.Random(1))
        sequence = [mode for mode, count in steps for _ in range(count)]
        width = 0.54
        gap = 0.003
        cell = (width - gap * (len(sequence) - 1)) / len(sequence)
        for i, mode in enumerate(sequence):
            self._summary_bar(left + cell / 2 + i * (cell + gap), -0.12, cell, 0.03,
                              mode_color(mode))
        self._summary_text("порядок заданий" + (" (пример)" if self.plan["order"] == "mixed"
                                                 else ""),
                           (left, -0.155), 0.75, "muted")

    def _summary_text(self, text, position, size, tone, origin=(-0.5, 0)):
        self.summary_objects.append(label(text, position, size, tone, origin=origin))

    def _summary_bar(self, x, y, width, height, hex_color):
        self.summary_objects.append(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                                           position=(x, y, FRONT), scale=(width, height),
                                           color=color.hex(hex_color)))

    # ---------- запуск ----------
    def start(self):
        try:
            plan = validate_plan(self.plan)
        except ValueError as error:
            self.error.text = str(error)
            return
        self.on_save(plan)
        steps = build_steps(plan["modes"], plan["per_mode"], plan["order"])
        playlist = Playlist(steps, plan["level"], plan["adaptive"])
        mode, _ = playlist.current
        self.navigate(mode, playlist=playlist)

    def close(self):
        for obj in self.summary_objects:
            destroy(obj)
        self.summary_objects = []
        super().close()
