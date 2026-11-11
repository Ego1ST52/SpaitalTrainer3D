"""Тренировка: серия заданий и её итоги. Без Ursina."""

from dataclasses import dataclass

from logic.scoring import task_points


@dataclass(frozen=True)
class TaskResult:
    correct: bool
    seconds: float
    points: int


def format_duration(seconds):
    """Секунды -> 'мм:сс'."""
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class TrainingSession:
    def __init__(self, mode, level, length=10, code=None, locked=False):
        if length < 1:
            raise ValueError("В тренировке должно быть хотя бы одно задание")
        self.mode = mode
        self.level = level
        self.length = length
        self.code = code        # код тренировки (см. logic/training_code.py)
        self.locked = locked    # True - тренировка по чужому коду
        self.results = []

    def record(self, correct, seconds):
        """Записать результат задания, вернуть начисленные баллы."""
        if self.is_finished:
            raise ValueError("Тренировка уже завершена")
        points = task_points(self.level, correct, seconds)
        self.results.append(TaskResult(bool(correct), seconds, points))
        return points

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