"""Подсказка «убрать неверный вариант» и её цена. Без Ursina.

Подсказка вычёркивает один неверный вариант ответа. За каждую подсказку
баллы за задание уменьшаются вдвое. Хотя бы два варианта всегда остаются,
иначе ответ был бы подарен целиком.
"""

import random

HINT_PENALTY = 0.5        # каждая подсказка умножает баллы на это число
MIN_LEFT = 2              # сколько вариантов остаётся после всех подсказок


def pick_hint(correct_index, options_count, removed, rng=random):
    """Какой вариант вычеркнуть: случайный неверный из ещё не вычеркнутых.
    None, если вычёркивать больше нельзя."""
    left = options_count - len(removed)
    if left <= MIN_LEFT:
        return None
    candidates = [i for i in range(options_count)
                  if i != correct_index and i not in removed]
    return rng.choice(candidates) if candidates else None


def hints_left(options_count, removed):
    """Сколько подсказок ещё можно взять."""
    return max(0, options_count - len(removed) - MIN_LEFT)


def points_with_hints(points, hints):
    """Баллы после подсказок: каждая уменьшает их вдвое (округляем вниз)."""
    return int(points * HINT_PENALTY ** hints)
