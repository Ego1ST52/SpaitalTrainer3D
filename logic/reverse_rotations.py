"""Режим «Найди повороты»: «Вращение куба» наоборот. Без Ursina.

Показаны два куба: «было» (исходное положение) и «стало». Нужно выбрать
цепочку поворотов, которая переводит первый куб во второй.

Правильный вариант - цепочка, по которой задание построено. Неверные
варианты - типичные ошибки (обратный порядок, обратные углы, пропущенный
поворот) и случайные цепочки. Каждый неверный вариант приводит к ДРУГОЙ
ориентации куба - это проверяется точно, матрицами из logic/rotations.py.
"""

import random
from dataclasses import dataclass

from logic.rotations import IDENTITY, apply_sequence
from logic.task_generator import mistaken_moves

REVERSE_LEVELS = {
    "easy":   {"moves": (1, 1), "angles": (90, -90), "options": 3},
    "medium": {"moves": (2, 2), "angles": (90, -90, 180), "options": 4},
    "hard":   {"moves": (3, 3), "angles": (90, -90, 180), "options": 4},
}

KIND_EXPLANATIONS = {
    "reversed": "Повороты те же, но в обратном порядке - а от порядка результат зависит.",
    "inverted": "Оси верные, но каждый поворот в обратную сторону (перепутаны + и -).",
    "skipped": "Здесь не хватает последнего поворота.",
    "random": "Эта цепочка приводит куб в другое положение.",
}


def moves_text(moves):
    """(('x', 90), ('y', -90)) -> 'X +90°,  Y -90°'."""
    return ",  ".join(f"{axis.upper()} {angle:+d}°" for axis, angle in moves)


@dataclass(frozen=True)
class ReverseTask:
    level: str
    moves: tuple          # правильная цепочка поворотов
    options: tuple        # варианты - цепочки поворотов
    correct_index: int
    kinds: tuple = ()     # 'correct', 'reversed', 'inverted', 'skipped' или 'random'

    @property
    def target(self):
        """Ориентация куба «стало» (матрица 3x3)."""
        return apply_sequence(IDENTITY, self.moves)

    @property
    def question(self):
        return "Какими поворотами получен куб справа?"

    @property
    def tags(self):
        return (f"moves:{len(self.moves)}",)

    def answer_tags(self, chosen_index):
        kind = self.kinds[chosen_index] if self.kinds else ""
        return (f"chose:rev_{kind}",) if kind in ("reversed", "inverted", "skipped") else ()

    def explain(self, chosen_index):
        if chosen_index == self.correct_index or not self.kinds:
            return None
        return KIND_EXPLANATIONS.get(self.kinds[chosen_index])


class ReverseTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def _random_moves(self, config):
        moves, previous = [], None
        for _ in range(self._rng.randint(*config["moves"])):
            axis = self._rng.choice([a for a in "xyz" if a != previous])
            moves.append((axis, self._rng.choice(config["angles"])))
            previous = axis
        return tuple(moves)

    def generate(self, level):
        if level not in REVERSE_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = REVERSE_LEVELS[level]
        while True:
            moves = self._random_moves(config)
            target = apply_sequence(IDENTITY, moves)
            if target == IDENTITY or moves == self._last:
                continue
            options = self._options(moves, target, config)
            if options is not None:
                break
        self._last = moves
        self._rng.shuffle(options)
        kinds = tuple(kind for _, kind in options)
        return ReverseTask(level, moves, tuple(m for m, _ in options),
                           kinds.index("correct"), kinds)

    def _options(self, moves, target, config):
        """[(цепочка, происхождение)]: правильная, типичные ошибки, случайные.
        Каждый неверный вариант даёт другую ориентацию, все тексты разные."""
        result = [(moves, "correct")]
        reached = {target}
        candidates = [(m, k) for k, m in mistaken_moves(moves).items() if m]
        for _ in range(40):
            candidates.append((self._random_moves(config), "random"))
        for candidate, kind in candidates:
            if len(result) == config["options"]:
                return result
            orientation = apply_sequence(IDENTITY, candidate)
            if orientation in reached:
                continue        # тоже верный (или такой уже есть) - не годится
            reached.add(orientation)
            result.append((candidate, kind))
        return result if len(result) == config["options"] else None
