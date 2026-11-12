import textwrap

from ursina import *
from ursina.shaders import unlit_shader

from core import settings, sounds
from engine.backdrop import FloatingCubes
from engine.objects import dispose
from interface.base_screen import BaseScreen
from interface.ui_kit import FRONT, label, Panel, Segmented, UIButton, with_alpha
from logic.achievements import ACHIEVEMENTS, progress
from logic.cube_skins import SKINS
from logic.goals import day_streak, tasks_on

GOLD = "#fbbf24"
CARD_W, CARD_H = 0.4, 0.2
COLUMNS = 4


def days_text(count):
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} день"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} дня"
    return f"{count} дней"


def goal_line(history, goal):
    """«Сегодня 7 из 20 заданий  •  серия 3 дня» - для экрана и меню."""
    from datetime import date
    today = tasks_on(history, date.today())
    streak = day_streak(history, goal)
    if goal and today >= goal:
        head = "цель дня выполнена"
    elif goal:
        head = f"сегодня {today} из {goal}"
    else:
        head = f"сегодня {today} заданий"
    return f"{head}  •  серия {days_text(streak)}"


class AchievementsScreen(BaseScreen):
    """Достижения и цель дня. history - тренировки игрока (или None),
    on_goal(цель) сохраняет новую цель дня."""

    def __init__(self, manager, history, goal, on_goal):
        super().__init__(manager)
        self.history = history or []
        self.goal = goal
        self.on_goal = on_goal
        self.cards = []
        self.own(FloatingCubes())

        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(label("Достижения", (left, 0.42), 2.0, "strong"))
        self.subtitle = self.own(label("", (left, 0.365), 0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06), variant="ghost"))

        self.own(label("Цель дня", (left, 0.275), 0.9))
        self.own(Segmented([(0, "Без цели"), (10, "10"), (20, "20"), (30, "30")], goal,
                           self.set_goal, position=(left + 0.42, 0.275), width=0.5,
                           text_size=0.8))
        self.goal_text = self.own(label("", (left + 0.7, 0.275), 0.85, GOLD))
        self.refresh()

    def set_goal(self, goal):
        self.goal = goal
        self.on_goal(goal)
        self.refresh()

    def refresh(self):
        for card in self.cards:
            dispose(card)    # карточка вместе со всем содержимым
        self.cards = []
        self.goal_text.text = goal_line(self.history, self.goal)

        done = 0
        for i, achievement in enumerate(ACHIEVEMENTS):
            row, col = divmod(i, COLUMNS)
            x = (col - (COLUMNS - 1) / 2) * (CARD_W + 0.025)
            y = 0.1 - row * (CARD_H + 0.03)
            value = progress(achievement.key, self.history, self.goal)
            unlocked = value >= achievement.target
            done += unlocked
            self.cards.append(self._card(achievement, value, unlocked, (x, y)))
        self.subtitle.text = (f"Открыто {done} из {len(ACHIEVEMENTS)}  •  "
                              "некоторые открывают новые скины куба")

    def _card(self, achievement, value, unlocked, position):
        card = Entity(parent=camera.ui, position=position)
        Panel(CARD_W, CARD_H, border=GOLD if unlocked else settings.BORDER, parent=card)
        left = -CARD_W / 2 + 0.025
        # Медаль: золотой кружок у полученных, тусклый у остальных
        Entity(parent=card, model="circle", scale=0.05, position=(left + 0.025, 0.055, FRONT),
               color=color.hex(GOLD) if unlocked else with_alpha(settings.TEXT_MUTED, 0.4),
               shader=unlit_shader)
        number = label(str(ACHIEVEMENTS.index(achievement) + 1), (left + 0.025, 0.056), 0.9,
                       "#0b1220" if unlocked else "muted", origin=(0, 0), parent=card)
        number.z = FRONT * 2                    # поверх кружка-медали
        label(achievement.title, (left + 0.065, 0.065), 1.0,
              "strong" if unlocked else "text", parent=card)
        label("получено" if unlocked else "в процессе", (left + 0.065, 0.035), 0.7,
              GOLD if unlocked else "muted", parent=card)
        label(textwrap.fill(achievement.description, 36), (left, -0.012), 0.75, "muted",
              parent=card)

        # Полоска прогресса
        bar_w = CARD_W - 0.05
        y = -0.055
        Entity(parent=card, model="quad", shader=unlit_shader, position=(0, y, FRONT),
               scale=(bar_w, 0.008), color=color.hex(settings.BORDER))
        share = value / achievement.target
        if share > 0:
            Entity(parent=card, model="quad", shader=unlit_shader, origin=(-0.5, 0),
                   position=(-bar_w / 2, y, FRONT * 1.5), scale=(bar_w * share, 0.008),
                   color=color.hex(GOLD if unlocked else settings.ACCENT))
        label(f"{value} / {achievement.target}", (CARD_W / 2 - 0.025, y - 0.022), 0.7,
              "muted", origin=(0.5, 0), parent=card)
        if achievement.reward_skin:
            label(f"награда: скин «{SKINS[achievement.reward_skin]['title']}»",
                  (left, y - 0.022), 0.7, GOLD if unlocked else "text", parent=card)
        return card

    def close(self):
        for card in self.cards:
            dispose(card)    # карточка вместе со всем содержимым
        self.cards = []
        super().close()


class AchievementToast(Entity):
    """Баннер «Новое достижение!» на экране итогов."""

    def __init__(self, achievements, position=None):
        super().__init__(parent=camera.ui,
                         position=position or (window.top_right.x - 0.24, 0.33))
        sounds.play("achievement")
        width = 0.42
        lines = []
        for a in achievements:
            lines.append(a.title)
            if a.reward_skin:
                lines.append(f"   открыт скин «{SKINS[a.reward_skin]['title']}»")
        height = 0.06 + 0.032 * len(lines)
        Panel(width, height, border=GOLD, parent=self)
        top = height / 2 - 0.03
        label("Новое достижение!" if len(achievements) == 1 else "Новые достижения!",
              (-width / 2 + 0.025, top), 0.9, GOLD, parent=self)
        for i, line in enumerate(lines):
            label(line, (-width / 2 + 0.025, top - 0.035 - i * 0.032), 0.85,
                  "text" if line.startswith(" ") else "strong", parent=self)
