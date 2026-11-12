"""Режим «Взгляд наблюдателя»: на столе стоят цветные башенки, у края стола -
человечек. Что он видит? Выбрать картинку: башенки слева направо так, как
их видит он, а не вы. Без Ursina - проверяется автотестами.

Башенки стоят в разных рядах и столбцах стола, поэтому с любой стороны
ни одна не загораживает другую, и картинка однозначна.

Стороны (оси как в Ursina: x - вправо, z - от нас вглубь):
  front - человечек на нашей стороне (z < 0), смотрит вглубь: слева направо = +x
  right - справа (x > 0), смотрит влево:      слева направо = +z
  back  - напротив нас (z > 0), смотрит на нас: слева направо = -x
  left  - слева (x < 0), смотрит вправо:      слева направо = -z
"""

import random
from dataclasses import dataclass

TOWER_COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#facc15", "#a855f7"]
COLOR_NAMES = {"#ef4444": "красная", "#3b82f6": "синяя", "#22c55e": "зелёная",
               "#facc15": "жёлтая", "#a855f7": "фиолетовая"}
SIDES = ("front", "right", "back", "left")
SIDE_WORDS = {"front": "с вашей стороны", "right": "справа", "back": "напротив вас",
              "left": "слева"}
# Как сторона превращает клетку стола (x, z) в «насколько левее-правее»
_ACROSS = {"front": lambda x, z: x, "right": lambda x, z: z,
           "back": lambda x, z: -x, "left": lambda x, z: -z}

OBSERVER_LEVELS = {
    "easy":   {"towers": 3, "sides": ("back", "right"), "options": 3},
    "medium": {"towers": 4, "sides": ("back", "right", "left"), "options": 4},
    "hard":   {"towers": 5, "sides": ("back", "right", "left"), "options": 4},
}


@dataclass(frozen=True)
class Tower:
    x: int
    z: int
    height: int
    color: str


def view_from(towers, side):
    """Картинка: башенки (цвет, высота) в порядке слева направо для наблюдателя."""
    across = _ACROSS[side]
    return tuple((t.color, t.height) for t in sorted(towers, key=lambda t: across(t.x, t.z)))


@dataclass(frozen=True)
class ObserverTask:
    level: str
    towers: tuple
    side: str             # где стоит наблюдатель
    options: tuple        # картинки
    correct_index: int
    kinds: tuple = ()     # откуда картинка: 'correct', 'own' (ваш вид), 'side:right', ...

    @property
    def question(self):
        return f"Что видит человечек {SIDE_WORDS[self.side]}?"

    @property
    def tags(self):
        return (f"side:{self.side}", f"towers:{len(self.towers)}")

    def answer_tags(self, chosen_index):
        kind = self.kinds[chosen_index] if self.kinds else ""
        if kind == "own":
            return ("chose:own_view",)        # выбрал то, что видит сам игрок
        if kind == "mirror":
            return ("chose:observer_mirror",)
        return ()

    def explain(self, chosen_index):
        kind = self.kinds[chosen_index] if self.kinds else ""
        if kind == "own":
            return "Это вид с вашей стороны, а не с места человечка."
        if kind == "mirror":
            return "Порядок перевёрнут: представьте, что вы встали на место человечка."
        if kind.startswith("side:"):
            return f"Так башенки видны {SIDE_WORDS[kind[5:]]}."
        return None


class ObserverTaskGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)

    def generate(self, level):
        if level not in OBSERVER_LEVELS:
            raise ValueError(f"Неизвестный уровень: {level!r}")
        config = OBSERVER_LEVELS[level]
        count = config["towers"]
        while True:
            # Разные столбцы и разные ряды: никто никого не загораживает
            xs = self._rng.sample(range(-2, 3), count)
            zs = self._rng.sample(range(-2, 3), count)
            colors = self._rng.sample(TOWER_COLORS, count)
            towers = tuple(Tower(x, z, self._rng.randint(1, 3), c)
                           for x, z, c in zip(xs, zs, colors))
            side = self._rng.choice(config["sides"])
            options = self._options(towers, side, config["options"])
            if options is not None:
                break
        self._rng.shuffle(options)
        kinds = tuple(kind for _, kind in options)
        return ObserverTask(level, towers, side, tuple(p for p, _ in options),
                            kinds.index("correct"), kinds)

    @staticmethod
    def _options(towers, side, needed):
        correct = view_from(towers, side)
        candidates = [(correct, "correct"), (view_from(towers, "front"), "own"),
                      (tuple(reversed(correct)), "mirror")]
        candidates += [(view_from(towers, other), f"side:{other}")
                       for other in SIDES if other not in (side, "front")]
        result, seen = [], set()
        for picture, kind in candidates:
            if picture not in seen:
                seen.add(picture)
                result.append((picture, kind))
            if len(result) == needed:
                return result
        return None
