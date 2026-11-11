"""Цель дня и серия дней. Без Ursina и без базы: на вход - история тренировок
из Database.get_history() (поле played_at - дата и время в формате ISO).

Цель дня - сколько заданий решить за день (0 - без цели: засчитывается
любая тренировка). Серия - сколько дней подряд цель выполнялась.
"""

from datetime import date, datetime, timedelta

GOAL_OPTIONS = (0, 10, 20, 30)


def played_day(entry):
    return datetime.fromisoformat(entry["played_at"]).date()


def tasks_on(history, day):
    """Сколько заданий решено (всего, не только верно) в день day."""
    return sum(h["tasks_total"] for h in history if played_day(h) == day)


def goal_met(history, day, goal):
    return tasks_on(history, day) >= max(goal, 1)


def day_streak(history, goal, today=None):
    """Серия дней подряд с выполненной целью. Если сегодня цель ещё не
    выполнена, серия не прерывается - считаем от вчерашнего дня."""
    today = today or date.today()
    day = today if goal_met(history, today, goal) else today - timedelta(days=1)
    streak = 0
    while goal_met(history, day, goal):
        streak += 1
        day -= timedelta(days=1)
    return streak


def best_streak(history, goal):
    """Самая длинная серия за всё время."""
    days = sorted({played_day(h) for h in history})
    best = current = 0
    previous = None
    for day in days:
        if not goal_met(history, day, goal):
            current, previous = 0, None
            continue
        current = current + 1 if previous == day - timedelta(days=1) else 1
        best = max(best, current)
        previous = day
    return best
