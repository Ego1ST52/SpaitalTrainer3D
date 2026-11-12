"""Тренировка: серия заданий и её итоги. Без Ursina."""

from collections import Counter
from dataclasses import dataclass

from logic.adaptive import LEVEL_ORDER
from logic.hints import points_with_hints
from logic.scoring import task_points


@dataclass(frozen=True)
class TaskResult:
    correct: bool
    seconds: float
    points: int
    level: str = ""       # уровень, на котором было это задание
    tags: tuple = ()      # метки задания для анализа ошибок, например ('axis:z',)


def format_duration(seconds):
    """Секунды -> 'мм:сс'."""
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class TrainingSession:
    def __init__(self, mode, level, length=10, code=None, locked=False, adaptive=None):
        if length < 1:
            raise ValueError("В тренировке должно быть хотя бы одно задание")
        self.mode = mode
        self.level = level      # уровень на старте
        # adaptive - AdaptiveLevel (logic/adaptive.py) или None. Если он есть,
        # уровень следующего задания меняется по ходу тренировки.
        self.adaptive = adaptive
        self.length = length
        self.code = code        # код тренировки (см. logic/training_code.py)
        self.locked = locked    # True - тренировка по чужому коду
        self.results = []
        self.level_change = None   # 'up' / 'down' после последнего ответа

    @property
    def current_level(self):
        """Уровень следующего задания."""
        return self.adaptive.level if self.adaptive else self.level

    def record(self, correct, seconds, tags=(), hints=0):
        """Записать результат задания, вернуть начисленные баллы.
        hints - сколько подсказок взято: каждая уменьшает баллы вдвое,
        а в метки задания добавляется 'hint' (для анализа).
        Баллы считаются по уровню, на котором было задание. Если сложность
        адаптивная, после ответа уровень может смениться: см. level_change."""
        if self.is_finished:
            raise ValueError("Тренировка уже завершена")
        level = self.current_level
        points = points_with_hints(task_points(level, correct, seconds), hints)
        if hints:
            tags = tuple(tags) + ("hint",)
        self.results.append(TaskResult(bool(correct), seconds, points, level, tuple(tags)))
        self.level_change = self.adaptive.record(correct) if self.adaptive else None
        return points

    @property
    def summary_level(self):
        """Основной уровень тренировки (для базы и статистики): тот, на котором
        было больше всего заданий; при равенстве - более высокий."""
        if not self.results:
            return self.level
        counts = Counter(r.level for r in self.results)
        return max(counts, key=lambda lvl: (counts[lvl], LEVEL_ORDER.index(lvl)))

    @property
    def levels_path(self):
        """Уровни по порядку без повторов подряд: ['easy', 'medium', 'easy']."""
        path = []
        for result in self.results:
            if not path or path[-1] != result.level:
                path.append(result.level)
        return path or [self.level]

    @property
    def total(self):
        return len(self.results)

    @property
    def correct(self):
        return sum(1 for r in self.results if r.correct)

    @property
    def wrong(self):
        return self.total - self.correct

    @property
    def accuracy(self):
        """Точность в процентах (0, если заданий ещё не было)."""
        return 100 * self.correct / self.total if self.total else 0.0

    @property
    def points(self):
        return sum(r.points for r in self.results)

    @property
    def total_time(self):
        return sum(r.seconds for r in self.results)

    @property
    def average_time(self):
        return self.total_time / self.total if self.total else 0.0

    @property
    def is_finished(self):
        return self.total >= self.length