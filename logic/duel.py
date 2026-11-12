"""Игра вдвоём за одним компьютером (дуэль). Без Ursina.

Оба игрока по очереди проходят ОДНИ И ТЕ ЖЕ задания: тренировка запускается
по общему коду (одно «зерно» генератора). Побеждает тот, у кого больше
верных ответов; при равенстве - больше баллов; потом - кто быстрее.
"""

import random
from dataclasses import dataclass, field

from logic.training_code import make_code


@dataclass
class Duel:
    players: list          # [{"id", "name", "color"}, {...}] - ровно двое
    mode: str
    level: str
    seed: int = field(default_factory=lambda: random.randint(0, 9999))
    sessions: list = field(default_factory=list)    # завершённые тренировки по очереди

    def __post_init__(self):
        if len(self.players) != 2 or self.players[0]["id"] == self.players[1]["id"]:
            raise ValueError("В дуэли участвуют два разных игрока.")

    @property
    def code(self):
        return make_code(self.mode, self.level, self.seed)

    @property
    def turn(self):
        """Номер игрока, который сейчас играет (0 или 1)."""
        return len(self.sessions)

    @property
    def current_player(self):
        return self.players[self.turn]

    @property
    def is_done(self):
        return len(self.sessions) == 2

    def finish_turn(self, session):
        if self.is_done:
            raise ValueError("Дуэль уже закончена.")
        if session.code != self.code:
            raise ValueError("Это тренировка не из этой дуэли.")
        self.sessions.append(session)

    def winner(self):
        """Номер победителя (0 или 1) или None при полной ничьей."""
        a, b = self.sessions

        def score(s):
            # Больше верных, больше баллов, меньше времени
            return (s.correct, s.points, -round(s.total_time, 1))
        if score(a) == score(b):
            return None
        return 0 if score(a) > score(b) else 1

    def rematch(self):
        """Новая дуэль тех же игроков: другие задания, первым ходит второй."""
        return Duel(list(reversed(self.players)), self.mode, self.level)
