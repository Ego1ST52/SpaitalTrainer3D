"""«Моя тренировка»: несколько режимов в одной тренировке. Без Ursina.

Тренировка - это список шагов [(режим, сколько заданий), ...]. Каждый шаг
проходит на экране своего режима, а Playlist хранит общий прогресс.
  блоками:      [('rotation', 3), ('projection', 3)]
  вперемешку:   [('projection', 1), ('rotation', 1), ('projection', 1), ...]
"""

import random

from logic.adaptive import AdaptiveLevel
from logic.session import TrainingSession

MODE_ORDER = ["rotation", "matching", "projection", "construction",
              "nets", "sections", "count", "memory", "shadow"]
PER_MODE_OPTIONS = (3, 5, 10)
ORDERS = ("blocks", "mixed")


def validate_plan(plan):
    """Проверить настройки своей тренировки (словарь). Ошибка - ValueError."""
    modes = plan.get("modes")
    if not modes or any(m not in MODE_ORDER for m in modes) or len(set(modes)) != len(modes):
        raise ValueError("Выберите хотя бы один режим.")
    if plan.get("level") not in ("easy", "medium", "hard"):
        raise ValueError("Неизвестный уровень.")
    if plan.get("per_mode") not in PER_MODE_OPTIONS:
        raise ValueError("Неверное число заданий.")
    if plan.get("order") not in ORDERS:
        raise ValueError("Неверный порядок.")
    if not isinstance(plan.get("adaptive"), bool):
        raise ValueError("Неверная настройка адаптивности.")
    return plan


def build_steps(modes, per_mode, order, rng=random):
    """Список шагов тренировки. Режимы идут в постоянном порядке MODE_ORDER."""
    modes = [m for m in MODE_ORDER if m in modes]
    if order == "blocks":
        return [(mode, per_mode) for mode in modes]

    # Вперемешку: каждый раз берём случайный режим из тех, у которых осталось
    # больше всего заданий, но не тот же, что был только что (если можно).
    left = {mode: per_mode for mode in modes}
    sequence = []
    while any(left.values()):
        previous = sequence[-1] if sequence else None
        candidates = [m for m in modes if left[m] > 0 and m != previous] or \
                     [m for m in modes if left[m] > 0]
        most = max(left[m] for m in candidates)
        mode = rng.choice([m for m in candidates if left[m] == most])
        left[mode] -= 1
        sequence.append(mode)

    steps = []                       # подряд идущие одинаковые режимы - один шаг
    for mode in sequence:
        if steps and steps[-1][0] == mode:
            steps[-1] = (mode, steps[-1][1] + 1)
        else:
            steps.append((mode, 1))
    return steps


class Playlist:
    def __init__(self, steps, level, adaptive=False):
        if not steps:
            raise ValueError("В тренировке должен быть хотя бы один шаг")
        self.steps = list(steps)
        self.level = level
        # Один общий «адаптивный уровень» на всю тренировку: он переходит
        # из режима в режим вместе с игроком.
        self.adaptive = AdaptiveLevel(level) if adaptive else None
        self.index = 0
        self.sessions = []           # завершённые шаги (TrainingSession)

    @property
    def current(self):
        """(режим, сколько заданий) текущего шага."""
        return self.steps[self.index]

    @property
    def is_done(self):
        return self.index >= len(self.steps)

    @property
    def total_tasks(self):
        return sum(count for _, count in self.steps)

    @property
    def tasks_done(self):
        return sum(s.total for s in self.sessions)

    def finish_step(self, session):
        self.sessions.append(session)
        self.index += 1

    def merged_by_mode(self):
        """Итоги по режимам: одна TrainingSession на режим (для базы и экрана).
        Так «вперемешку» не превращается в кучу записей по одному заданию."""
        merged = []
        for mode in MODE_ORDER:
            results = [r for s in self.sessions if s.mode == mode for r in s.results]
            if results:
                session = TrainingSession(mode, results[0].level, length=len(results))
                session.results = list(results)
                merged.append(session)
        return merged

    # ---------- общие итоги ----------
    @property
    def all_results(self):
        return [r for s in self.sessions for r in s.results]

    @property
    def correct(self):
        return sum(r.correct for r in self.all_results)

    @property
    def accuracy(self):
        total = len(self.all_results)
        return 100 * self.correct / total if total else 0.0

    @property
    def points(self):
        return sum(r.points for r in self.all_results)

    @property
    def total_time(self):
        return sum(r.seconds for r in self.all_results)
