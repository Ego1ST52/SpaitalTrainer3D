"""Генерация заданий на вращение. Без Ursina: всё проверяется тестами."""

import random
from dataclasses import dataclass

from core import settings
from logic.rotations import IDENTITY, apply_sequence, face_at

# Параметры уровней сложности
# targets - о какой стороне спрашиваем: на начальном уровне только «сверху»,
# дальше ещё «спереди» и «справа» (надо следить за всем кубом, а не за одной гранью)
LEVELS = {
    "easy":   {"moves": (1, 1), "angles": (90, 180), "options": 3, "targets": ("+Y",)},
    "medium": {"moves": (2, 3), "angles": (90, -90, 180), "options": 4,
               "targets": ("+Y", "+Y", "-Z")},
    "hard":   {"moves": (4, 5), "angles": (90, -90, 180), "options": 5,
               "targets": ("+Y", "-Z", "+X")},
}

# Стороны, о которых спрашиваем (куда смотрит грань в итоге)
TARGET_WORDS = {"+Y": "сверху", "-Z": "спереди", "+X": "справа"}

# Типичные ошибки - как получается неверный вариант
MISTAKE_TEXTS = {
    "reversed": "если выполнить повороты в обратном порядке",
    "skipped": "если пропустить последний поворот",
    "inverted": "если крутить в обратную сторону (перепутать + и -)",
    "start": "если куб вообще не поворачивать",
}


def top_color(orientation, face_names=None, target="+Y"):
    """Название грани, которая при этой ориентации смотрит в сторону target
    (по умолчанию вверх). face_names - {грань: название} из скина куба."""
    names = face_names or settings.FACE_COLOR_NAMES
    return names[face_at(orientation, target)]


def mistaken_moves(moves):
    """Повороты, которые получаются при типичных ошибках: {ошибка: повороты}."""
    return {
        "reversed": tuple(reversed(moves)),
        "skipped": tuple(moves[:-1]),
        "inverted": tuple((axis, -angle) for axis, angle in moves),
        "start": (),
    }


@dataclass(frozen=True)
class RotationTask:
    level: str
    moves: tuple          # ((ось, угол), ...)
    options: tuple        # названия цветов - варианты ответа
    correct_index: int    # индекс правильного варианта
    target: str = "+Y"    # о какой стороне вопрос: '+Y' сверху, '-Z' спереди, '+X' справа
    kinds: tuple = ()     # для каждого варианта: 'correct', ошибка из MISTAKE_TEXTS или 'random'

    @property
    def target_word(self):
        return TARGET_WORDS[self.target]

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def tags(self):
        """Метки для анализа ошибок: вокруг каких осей и сколько поворотов."""
        axes = sorted({axis for axis, _ in self.moves})
        tags = [f"axis:{axis}" for axis in axes] + [f"moves:{len(self.moves)}"]
        if any(abs(angle) == 180 for _, angle in self.moves):
            tags.append("angle:180")
        tags.append(f"target:{self.target}")
        return tuple(tags)

    def _kind(self, index):
        return self.kinds[index] if self.kinds else "random"

    def answer_tags(self, chosen_index):
        """Какую типичную ошибку выдаёт выбранный неверный вариант."""
        kind = self._kind(chosen_index)
        return (f"chose:{kind}",) if kind in MISTAKE_TEXTS else ()

    def explain(self, chosen_index):
        """Почему выбранный вариант неверен (или None, если объяснить нечем)."""
        kind = self._kind(chosen_index)
        if kind not in MISTAKE_TEXTS:
            return None
        return (f"Вариант «{self.options[chosen_index].capitalize()}» был бы верным, "
                f"{MISTAKE_TEXTS[kind]}.")

    def describe_moves(self):
        parts = []
        for number, (axis, angle) in enumerate(self.moves, start=1):
            parts.append(f"{number}) вокруг оси {axis.upper()} на {angle:+d}°")
        return "; ".join(parts)

    @property
    def question(self):
        return ("Сейчас сверху белая грань, спереди зелёная. "
                f"Повороты: {self.describe_moves()}. "
                f"Какая грань окажется {self.target_word}?")


class RotationTaskGenerator:
    def __init__(self, seed=None, face_names=None):
        self._rng = random.Random(seed)
        self._last_moves = None
        # Названия граней зависят от скина куба (цвета или цифры кости)
        self._names = face_names or settings.FACE_COLOR_NAMES

    def generate(self, level):
        if level not in LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = LEVELS[level]

        # Повторяем, пока не получим подходящую последовательность
        while True:
            moves = self._random_moves(config)
            if moves == self._last_moves:
                continue  # то же задание подряд не нужно
            if apply_sequence(IDENTITY, moves) == IDENTITY:
                continue  # куб вернулся в исходное положение - скучно
            break
        self._last_moves = moves

        target = self._rng.choice(config["targets"])
        correct = top_color(apply_sequence(IDENTITY, moves), self._names, target)
        options, kinds = self._build_options(moves, correct, config["options"], target)
        return RotationTask(level, moves, tuple(options), options.index(correct), target,
                            tuple(kinds))

    def _random_moves(self, config):
        count = self._rng.randint(*config["moves"])
        moves = []
        previous_axis = None
        for _ in range(count):
            # не крутим дважды подряд вокруг одной оси
            axis = self._rng.choice([a for a in "xyz" if a != previous_axis])
            angle = self._rng.choice(config["angles"])
            moves.append((axis, angle))
            previous_axis = axis
        return tuple(moves)

    def _build_options(self, moves, correct, total, target="+Y"):
        """Варианты ответа и их «происхождение». Сначала - ответы, которые
        получаются при типичных ошибках, потом случайные грани."""
        kinds = {correct: "correct"}
        for kind, wrong_moves in mistaken_moves(moves).items():
            name = top_color(apply_sequence(IDENTITY, wrong_moves), self._names, target)
            if name not in kinds and len(kinds) < total:
                kinds[name] = kind

        # Добираем случайными цветами, если вариантов не хватило
        others = [c for c in self._names.values() if c not in kinds]
        self._rng.shuffle(others)
        for name in others[: total - len(kinds)]:
            kinds[name] = "random"

        options = list(kinds)
        self._rng.shuffle(options)
        return options, [kinds[name] for name in options]