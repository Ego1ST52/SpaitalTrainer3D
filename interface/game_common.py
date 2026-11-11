"""Общее для всех игровых экранов: как начинается и чем заканчивается тренировка."""

from core.preferences import prefs
from logic.adaptive import AdaptiveLevel
from logic.session import TrainingSession
from logic.training_code import CODE_LENGTH, make_code, random_seed

LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}


def new_training(mode, level, seed=None, locked=False, playlist=None):
    """Создать тренировку. Возвращает (session, seed).

    seed - зерно генератора заданий: одно зерно даёт одни и те же задания.
    Если его нет - берём случайное. По зерну строится код тренировки,
    который показывается на экране результатов.
    locked=True - тренировка по коду: число заданий фиксировано (чтобы у
    всех, кто ввёл код, было поровну), а уровень менять нельзя.
    playlist - шаг «Моей тренировки» (logic/playlist.py)."""
    if seed is None:
        seed = random_seed()

    if playlist is not None:
        # Шаг своей тренировки: число заданий и уровень берём из плана,
        # адаптивный уровень общий на все шаги
        _, length = playlist.current
        adaptive = playlist.adaptive
        start = adaptive.level if adaptive else playlist.level
        session = TrainingSession(mode, start, length, locked=True, adaptive=adaptive)
        session.playlist = playlist     # верхняя панель покажет общий прогресс
        session.note = "Моя тренировка"
        return session, seed

    if locked:
        session = TrainingSession(mode, level, CODE_LENGTH[mode],
                                  code=make_code(mode, level, seed), locked=True)
        session.note = f"тренировка по коду {session.code}"
        return session, seed

    adaptive = AdaptiveLevel(level) if prefs.get("adaptive") else None
    session = TrainingSession(mode, level, prefs.session_length(mode),
                              code=make_code(mode, level, seed), adaptive=adaptive)
    session.note = ("адаптивная сложность" if adaptive
                    else "сменить: клавиши 1, 2, 3")
    return session, seed


def finish_label(screen):
    """Подпись кнопки после последнего задания."""
    playlist = screen.playlist
    if playlist is not None and playlist.index < len(playlist.steps) - 1:
        return "Следующий этап"
    return "Результаты"


def finish_training(screen):
    """Тренировка (или этап своей тренировки) закончена - куда дальше."""
    playlist = screen.playlist
    if playlist is None:
        screen.navigate("results", session=screen.session)
        return
    playlist.finish_step(screen.session)
    if playlist.is_done:
        screen.navigate("custom_results", playlist=playlist)
    else:
        mode, _ = playlist.current
        screen.navigate(mode, playlist=playlist)
