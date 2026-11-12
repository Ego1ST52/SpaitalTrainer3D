"""Экран «Исследование»: входной и итоговый тест (помогает ли тренажёр)
и опыт «время ответа против угла поворота»."""

import textwrap

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from interface.base_screen import BaseScreen
from interface.ui_kit import FRONT, label, mode_color, Panel, UIButton
from logic.assessment import STAGE_NAMES, TEST_STEPS, compare, make_test
from logic.experiment import (ANGLES, MIN_ANSWERS, angle_table, conclusion,
                              experiment_points, trend)

LEFT_X = -0.43            # центр левой панели (тест)
RIGHT_X = 0.43            # центр правой панели (опыт)
PANEL_W = 0.82
CHART_BOTTOM = -0.17
CHART_HEIGHT = 0.24


class ResearchScreen(BaseScreen):
    """assessment - {'pre': итоги, 'post': итоги} из настроек игрока,
    log - журнал заданий (или None, если база недоступна),
    message - что сказать сверху (например, «Входной тест сохранён»)."""

    def __init__(self, manager, assessment, log, message=""):
        super().__init__(manager)
        self.assessment = assessment or {}
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(label("Исследование", (left, 0.42), 2.0, "strong"))
        self.own(label(message or "Проверьте на себе: помогает ли тренажёр и как вы "
                                  "поворачиваете фигуры в уме", (left, 0.365), 0.85,
                       "accent" if message else "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06), variant="ghost"))
        self.own(Panel(PANEL_W, 0.72, position=(LEFT_X, -0.06)))
        self.own(Panel(PANEL_W, 0.72, position=(RIGHT_X, -0.06)))
        self._test_panel()
        self._experiment_panel(log)
        self.own(label("Показатели отражают результаты в игре и не доказывают изменения "
                       "когнитивных способностей.", (0, -0.455), 0.75, "muted",
                       origin=(0, 0)))

    # ---------- тест до и после ----------
    def _test_panel(self):
        x0 = LEFT_X - PANEL_W / 2 + 0.03
        self.own(label("Тест до и после", (x0, 0.26), 1.15, "strong"))
        tasks = sum(count for _, count in TEST_STEPS)
        self.own(label(textwrap.fill(
            f"{tasks} заданий из 5 режимов, без подсказок. Пройдите входной тест, "
            "потренируйтесь несколько дней, затем - итоговый.", 66),
            (x0, 0.215), 0.75, "muted", origin=(-0.5, 0.5)))
        pre, post = self.assessment.get("pre"), self.assessment.get("post")
        y = 0.08
        for title, x in (("", x0), ("до", LEFT_X - 0.02), ("после", LEFT_X + 0.13),
                         ("изменение", LEFT_X + 0.3)):
            self.own(label(title, (x, y), 0.8, "muted", origin=(0, 0) if title else (-0.5, 0)))
        if pre and post:
            rows = compare(pre, post)
        else:
            known = pre or post
            rows = [("Точность", f"{pre['accuracy']:.0f}%" if pre else "-",
                     f"{post['accuracy']:.0f}%" if post else "-", "-", None),
                    ("Среднее время", f"{pre['seconds']:.1f} с" if pre else "-",
                     f"{post['seconds']:.1f} с" if post else "-", "-", None)] if known else []
        for i, (name, before, after, delta, better) in enumerate(rows):
            ry = y - 0.06 - i * 0.055
            tone = "text" if better is None else ("correct" if better else "wrong")
            self.own(label(name, (x0, ry), 0.9))
            self.own(label(before, (LEFT_X - 0.02, ry), 0.95, "strong", origin=(0, 0)))
            self.own(label(after, (LEFT_X + 0.13, ry), 0.95, "strong", origin=(0, 0)))
            self.own(label(delta, (LEFT_X + 0.3, ry), 0.95, tone, origin=(0, 0)))
        if not rows:
            self.own(label("Тестов ещё не было.", (x0, y - 0.07), 0.9, "muted"))
        for i, stage in enumerate(("pre", "post")):
            done = self.assessment.get(stage)
            note = f"пройден {done['date']}" if done else "не пройден"
            bx = LEFT_X - 0.19 + i * 0.38
            self.own(label(note, (bx, -0.27), 0.7, "muted", origin=(0, 0)))
            enabled = stage == "pre" or "pre" in self.assessment
            button = self.own(UIButton(STAGE_NAMES[stage], lambda s=stage: self.start_test(s),
                                       position=(bx, -0.33), scale=(0.36, 0.06),
                                       variant="primary" if enabled and not done else
                                       "secondary"))
            button.enabled = enabled
        if "pre" not in self.assessment:
            self.own(label("Итоговый тест откроется после входного", (LEFT_X + 0.19, -0.39),
                           0.65, "muted", origin=(0, 0)))

    def start_test(self, stage):
        playlist = make_test(stage)
        self.navigate(playlist.current[0], playlist=playlist)

    # ---------- опыт «время против угла» ----------
    def _experiment_panel(self, log):
        x0 = RIGHT_X - PANEL_W / 2 + 0.03
        self.own(label("Опыт: время против угла", (x0, 0.26), 1.15, "strong"))
        self.own(label(textwrap.fill(
            "Чем сильнее повёрнута фигура, тем дольше её узнают - так её поворачивают "
            "в уме (опыт Шепарда и Метцлер, 1971). Данные - ваши верные ответы "
            "в «Одинаковых фигурах».", 66), (x0, 0.215), 0.75, "muted", origin=(-0.5, 0.5)))
        points = experiment_points(log)
        table = angle_table(points)
        self._chart(table, points)
        self.own(label(textwrap.fill(conclusion(points), 64), (x0, -0.255), 0.78,
                       "text" if len(points) >= MIN_ANSWERS else "muted",
                       origin=(-0.5, 0.5)))
        self.own(UIButton("Пройти «Одинаковые фигуры»", self.start_matching,
                          position=(RIGHT_X, -0.39), scale=(0.42, 0.055), text_size=0.8))

    def _chart(self, table, points):
        """Столбики: среднее время для каждого угла, пунктир - прямая тренда."""
        accent = mode_color("matching")
        tallest = max([seconds for _, seconds in table.values()] + [1])
        width = 0.11
        for i, angle in enumerate(ANGLES):
            x = RIGHT_X - 0.24 + i * 0.16
            self.own(label(f"{angle}°", (x, CHART_BOTTOM - 0.025), 0.8, "muted", origin=(0, 0)))
            if angle not in table:
                self.own(label("нет", (x, CHART_BOTTOM + 0.02), 0.7, "muted", origin=(0, 0)))
                continue
            count, seconds = table[angle]
            height = CHART_HEIGHT * seconds / tallest
            self.own(Entity(parent=camera.ui, model="quad", shader=unlit_shader,
                            origin=(0, -0.5), position=(x, CHART_BOTTOM, FRONT),
                            scale=(width, height), color=color.hex(accent)))
            self.own(label(f"{seconds:.1f} с", (x, CHART_BOTTOM + height + 0.018), 0.75,
                           "strong", origin=(0, 0)))
            self.own(label(f"{count} отв.", (x, CHART_BOTTOM + 0.015), 0.6, "text",
                           origin=(0, 0)))
        line = trend(points) if len(points) >= MIN_ANSWERS else None
        if line:
            a, b = line
            # Точки прямой над первым и последним столбиком
            ends = []
            for i in (0, len(ANGLES) - 1):
                seconds = max(0.0, a + b * ANGLES[i])
                ends.append(Vec3(RIGHT_X - 0.24 + i * 0.16,
                                 CHART_BOTTOM + CHART_HEIGHT * seconds / tallest, FRONT * 2))
            self.own(Entity(parent=camera.ui, model=Mesh(vertices=ends, mode="line",
                                                         thickness=2),
                            color=color.hex(settings.TEXT_STRONG), shader=unlit_shader))

    def start_matching(self):
        self.navigate("matching", level="medium")
