"""Режим «Развёртка»: из плоской развёртки складывается куб. Без Ursina.

Развёртка - 6 клеток (столбец, строка) на плоскости. Как понять, какой
гранью куба станет каждая клетка? «Перекатываем» куб по клеткам, как по
полу: куб стоит на первой клетке, перекатывается на соседнюю - и той
гранью, которой он лёг на новую клетку, эта клетка и станет.
Повороты считаются точно, матрицами из logic/rotations.py.

Развёртка правильная, если все 6 граней получились разными - так генератор
сам находит все 11 развёрток куба.
"""

import random
from collections import deque
from dataclasses import dataclass

from logic.rotations import IDENTITY, all_orientations, face_at, rotate

LETTERS = "АБВГДЕ"
OPPOSITE = {"+X": "-X", "-X": "+X", "+Y": "-Y", "-Y": "+Y", "+Z": "-Z", "-Z": "+Z"}
NEIGHBOURS_2D = [(1, 0), (-1, 0), (0, 1), (0, -1)]

# Перекатиться на соседнюю клетку = повернуть куб на 90° вокруг оси:
# на восток (+столбец) - вокруг Z, на север (+строка) - вокруг X.
# Важно: при перекатывании клетка прижимается к грани напечатанной стороной,
# то есть буквы оказались бы ВНУТРИ куба - это зеркальный кубик. Настоящую
# развёртку складывают буквами НАРУЖУ, поэтому повороты на восток и запад
# взяты зеркально (это поймал автотест, сравнивающий логику с 3D-складыванием).
ROLL = {(1, 0): ("z", 90), (-1, 0): ("z", -90), (0, 1): ("x", 90), (0, -1): ("x", -90)}

NET_LEVELS = {
    "easy": {"kind": "opposite", "options": 3},
    "medium": {"kind": "opposite", "options": 5},
    "hard": {"kind": "cube", "options": 4},
}


def normalize2d(cells):
    min_c = min(c for c, _ in cells)
    min_r = min(r for _, r in cells)
    return tuple(sorted((c - min_c, r - min_r) for c, r in cells))


def fold(cells):
    """Сложить развёртку: {клетка: грань куба} ('+X', '-Y'...) или None,
    если клетки не связаны или две клетки попадают на одну грань."""
    cells = list(cells)
    if len(cells) != 6:
        return None
    start = cells[0]
    orientation = {start: IDENTITY}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for (dc, dr), (axis, angle) in ROLL.items():
            neighbour = (cell[0] + dc, cell[1] + dr)
            if neighbour in cells and neighbour not in orientation:
                orientation[neighbour] = rotate(orientation[cell], axis, angle)
                queue.append(neighbour)
    if len(orientation) != 6:
        return None                                   # клетки не связаны
    faces = {cell: face_at(o, "-Y") for cell, o in orientation.items()}
    return faces if len(set(faces.values())) == 6 else None


def is_net(cells):
    return fold(cells) is not None


def random_net(rng):
    """Случайная правильная развёртка куба (растим фигуру из 6 клеток)."""
    while True:
        cells = {(0, 0)}
        while len(cells) < 6:
            c, r = rng.choice(sorted(cells))
            dc, dr = rng.choice(NEIGHBOURS_2D)
            cells.add((c + dc, r + dr))
        cells = normalize2d(cells)
        if is_net(cells):
            return cells


def visible_triples(face_letters):
    """Какие тройки букв (сверху, спереди, справа) можно увидеть на кубе,
    если повернуть его как угодно. face_letters - {грань: буква}."""
    triples = set()
    for orientation in all_orientations():
        triples.add(tuple(face_letters[face_at(orientation, side)]
                          for side in ("+Y", "-Z", "+X")))
    return triples


@dataclass(frozen=True)
class NetTask:
    level: str
    kind: str              # 'opposite' - что напротив; 'cube' - какой куб получится
    cells: tuple           # клетки развёртки
    letters: tuple         # буква на каждой клетке (в порядке cells)
    marked: int            # для 'opposite': номер отмеченной клетки
    options: tuple         # буквы или тройки букв (сверху, спереди, справа)
    correct_index: int
    distractor_kinds: tuple = ()   # для 'cube': почему вариант неверный

    @property
    def correct_option(self):
        return self.options[self.correct_index]

    @property
    def face_letters(self):
        """{грань куба: буква} после складывания."""
        faces = fold(self.cells)
        return {faces[cell]: letter for cell, letter in zip(self.cells, self.letters)}

    @property
    def question(self):
        if self.kind == "opposite":
            return f"Какая буква окажется напротив «{self.letters[self.marked]}»?"
        return "Какой кубик можно сложить из этой развёртки?"

    @property
    def tags(self):
        return (f"type:{self.kind}",)

    def answer_tags(self, chosen_index):
        if chosen_index == self.correct_index:
            return ()
        if self.kind == "opposite":
            return ("chose:adjacent",)          # выбрали соседнюю, а не противоположную
        return (f"chose:{self.distractor_kinds[chosen_index]}",)


class NetTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)
        self._last = None

    def generate(self, level):
        if level not in NET_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = NET_LEVELS[level]
        while True:
            cells = random_net(self._rng)
            letters = list(LETTERS)
            self._rng.shuffle(letters)
            key = (cells, tuple(letters))
            if key != self._last:
                break
        self._last = key
        faces = fold(cells)
        face_letters = {faces[cell]: letter for cell, letter in zip(cells, letters)}

        if config["kind"] == "opposite":
            marked = self._rng.randrange(6)
            correct = face_letters[OPPOSITE[faces[cells[marked]]]]
            others = [l for l in letters if l not in (letters[marked], correct)]
            self._rng.shuffle(others)
            options = [correct] + others[:config["options"] - 1]
            self._rng.shuffle(options)
            return NetTask(level, "opposite", cells, tuple(letters), marked,
                           tuple(options), options.index(correct))

        valid = visible_triples(face_letters)
        correct = self._rng.choice(sorted(valid))
        wrong = self._wrong_cubes(correct, valid, face_letters, config["options"] - 1)
        pairs = [(correct, "correct")] + wrong
        self._rng.shuffle(pairs)
        options = tuple(t for t, _ in pairs)
        kinds = tuple(k for _, k in pairs)
        return NetTask(level, "cube", cells, tuple(letters), 0, options,
                       kinds.index("correct"), kinds)

    def _wrong_cubes(self, correct, valid, face_letters, needed):
        """Неверные кубики: зеркальный порядок граней или противоположные
        грани рядом. Каждый гарантированно нельзя сложить из развёртки."""
        letter_face = {letter: face for face, letter in face_letters.items()}
        candidates = []
        a, b, c = correct
        candidates.append(((a, c, b), "mirror"))            # те же грани, зеркально
        for triple in valid:
            x, y, z = triple
            candidates.append(((y, x, z), "mirror"))
        for triple in valid:                                # подменить одну грань на противоположную
            for i in range(3):
                swapped = list(triple)
                swapped[i] = face_letters[OPPOSITE[letter_face[triple[i]]]]
                candidates.append((tuple(swapped), "opposite"))
        self._rng.shuffle(candidates)
        result, used = [], {correct}
        for triple, kind in candidates:
            if triple not in valid and triple not in used and len(set(triple)) == 3:
                used.add(triple)
                result.append((triple, kind))
            if len(result) == needed:
                break
        return result
