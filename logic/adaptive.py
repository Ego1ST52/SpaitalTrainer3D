"""Адаптивная сложность: уровень подстраивается под игрока прямо во время
тренировки. Без Ursina - проверяется автотестами.

Правило простое и понятное игроку:
  * UP_AFTER верных ответов подряд  -> уровень выше (если есть куда);
  * DOWN_AFTER ошибок подряд        -> уровень ниже (если есть куда).
После смены уровня счётчики обнуляются - новому уровню даётся шанс.
"""

LEVEL_ORDER = ["easy", "medium", "hard"]
UP_AFTER = 3
DOWN_AFTER = 2


class AdaptiveLevel:
    def __init__(self, start="easy"):
        if start not in LEVEL_ORDER:
            raise ValueError(f"Неизвестный уровень: {start!r}")
        self.level = start
        self._correct_streak = 0
        self._wrong_streak = 0

    def record(self, correct):
        """Учесть ответ. Возвращает 'up', 'down' или None (уровень тот же)."""
        if correct:
            self._correct_streak += 1
            self._wrong_streak = 0
        else:
            self._wrong_streak += 1
            self._correct_streak = 0

        index = LEVEL_ORDER.index(self.level)
        if self._correct_streak >= UP_AFTER and index < len(LEVEL_ORDER) - 1:
            return self._change(index + 1, "up")
        if self._wrong_streak >= DOWN_AFTER and index > 0:
            return self._change(index - 1, "down")
        return None

    def _change(self, index, direction):
        self.level = LEVEL_ORDER[index]
        self._correct_streak = self._wrong_streak = 0
        return direction
