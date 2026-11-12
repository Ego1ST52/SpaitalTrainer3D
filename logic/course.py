"""«Путь новичка»: короткий курс из уроков, от простого к сложному. Без Ursina.

Урок - маленькая тренировка (один или несколько режимов). Урок пройден,
если точность не ниже его цели; тогда открывается следующий. Прогресс
игрока - число пройденных уроков (prefs "course").
"""

from dataclasses import dataclass

from logic.playlist import Playlist


@dataclass(frozen=True)
class Lesson:
    title: str
    steps: tuple          # ((режим, заданий), ...)
    level: str
    goal: int             # нужная точность, %
    tip: str              # чему учит урок


LESSONS = (
    Lesson("Первый поворот", (("rotation", 5),), "easy", 60,
           "один поворот куба - какая грань окажется сверху"),
    Lesson("Та же фигура", (("matching", 5),), "easy", 60,
           "узнать фигуру, повёрнутую по-другому"),
    Lesson("Взгляд сбоку", (("projection", 5),), "easy", 60,
           "как фигура выглядит спереди и сверху"),
    Lesson("Первая постройка", (("construction", 3),), "easy", 60,
           "собрать фигуру из кубиков по образцу"),
    Lesson("Куб наоборот", (("reverse", 5),), "easy", 60,
           "по двум кубам найти поворот"),
    Lesson("Считаем кубики", (("count", 5),), "easy", 70,
           "увидеть и скрытые кубики тоже"),
    Lesson("Развёртка", (("nets", 5),), "easy", 60,
           "какие грани куба окажутся напротив"),
    Lesson("Чужими глазами", (("observer", 5),), "easy", 60,
           "что видит человек с другой стороны стола"),
    Lesson("Два поворота", (("rotation", 5),), "medium", 70,
           "цепочка поворотов и порядок важен"),
    Lesson("Экзамен", (("rotation", 3), ("matching", 3), ("projection", 3)), "medium", 70,
           "всё вместе - вы готовы к обычным тренировкам"),
)


def lesson_playlist(index):
    """Тренировка урока index (без адаптивной сложности: уровень задан уроком)."""
    lesson = LESSONS[index]
    playlist = Playlist(list(lesson.steps), lesson.level, adaptive=False)
    playlist.lesson = index
    return playlist


def lesson_passed(playlist):
    return playlist.accuracy >= LESSONS[playlist.lesson].goal


def advance(progress, playlist):
    """Новый прогресс после урока: следующий открывается, только если пройден
    текущий последний открытый урок."""
    if lesson_passed(playlist) and playlist.lesson == progress:
        return min(progress + 1, len(LESSONS))
    return progress


def state(index, progress):
    """'done' - пройден, 'open' - можно проходить, 'locked' - ещё закрыт."""
    if index < progress:
        return "done"
    return "open" if index == progress else "locked"
