"""Общее для всех игровых экранов: как начинается тренировка."""

from core.preferences import prefs
from logic.session import TrainingSession
from logic.training_code import CODE_LENGTH, make_code, random_seed

LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}


def new_training(mode, level, seed=None, locked=False):
    """Создать тренировку. Возвращает (session, seed).

    seed - зерно генератора заданий: одно зерно даёт одни и те же задания.
    Если его нет - берём случайное. По зерну строится код тренировки,
    который показывается на экране результатов.
    locked=True - тренировка по коду: число заданий фиксировано (чтобы у
    всех, кто ввёл код, было поровну), а уровень менять нельзя."""
    if seed is None:
        seed = random_seed()
    length = CODE_LENGTH[mode] if locked else prefs.session_length(mode)
    session = TrainingSession(mode, level, length,
                              code=make_code(mode, level, seed), locked=locked)
    return session, seed
