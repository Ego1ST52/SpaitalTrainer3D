"""Откуда экран берёт задания. Без Ursina.

Генератор заданий работает от «зерна»: одно зерно и одна и та же
последовательность уровней дают одни и те же задания. Поэтому любое
задание можно потом воспроизвести, зная (зерно, уровни до него включительно) -
это его «ключ». Ключи нужны, чтобы:
  - повторить задание, в котором была ошибка («Повторить ошибки»);
  - продолжить недоигранную тренировку с того же места.
"""


class TrackingSource:
    """Обычный источник: генератор с зерном, который запоминает ключ каждого
    выданного задания (keys[i] - ключ i-го задания тренировки)."""

    def __init__(self, factory, seed):
        self.seed = seed
        self._generator = factory(seed)
        self.levels = []
        self.keys = []

    def generate(self, level):
        self.levels.append(level)
        self.keys.append((self.seed, tuple(self.levels)))
        return self._generator.generate(level)

    def fast_forward(self, levels):
        """Пропустить уже пройденные задания (для «Продолжить тренировку»):
        генератор выдаёт их заново и окажется ровно там, где остановились."""
        for level in levels:
            self.generate(level)


def replay(factory, seed, levels):
    """Воспроизвести задание по ключу: последнее из заданий с этими уровнями."""
    generator = factory(seed)
    task = None
    for level in levels:
        task = generator.generate(level)
    return task


class ReviewSource:
    """Источник для «Повторить ошибки»: выдаёт сохранённые задания по ключам.
    items - [{'seed': ..., 'levels': [...]}, ...]."""

    def __init__(self, factory, items):
        self._factory = factory
        self.items = list(items)
        self.keys = []

    def generate(self, level):
        item = self.items[len(self.keys) % len(self.items)]
        key = (item["seed"], tuple(item["levels"]))
        self.keys.append(key)
        return replay(self._factory, *key)
