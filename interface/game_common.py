"""Общее для всех игровых экранов: как начинается и чем заканчивается тренировка."""

import time

from core.preferences import prefs
from logic.adaptive import AdaptiveLevel
from logic.resume import restore, snapshot
from logic.session import TrainingSession
from logic.task_source import ReviewSource, TrackingSource
from logic.training_code import CODE_LENGTH, make_code, random_seed

BLITZ_SECONDS = 60          # «Блиц»: сколько длится тренировка

LEVEL_KEYS = {"1": "easy", "2": "medium", "3": "hard"}

# Дуэль, которая сейчас идёт («Игра вдвоём», см. logic/duel.py и main.py).
# Тренировка с кодом этой дуэли - ход одного из её игроков.
active_duel = None

# «Задания для класса»: код тренировки -> ограничение по времени, минут
# (заполняет main.py из базы, см. logic/class_tasks.py)
class_limits = {}

# Недоигранная тренировка, которую игрок решил продолжить (см. logic/resume.py):
# main.py кладёт её сюда перед открытием экрана режима
pending_resume = None


def _autosave(session):
    """После каждого ответа - сохранить недоигранную тренировку, а после
    последнего задания - забыть её (она уже в базе)."""
    try:
        prefs.save("resume", None if session.is_finished else snapshot(session))
    except (KeyError, ValueError):
        pass


def new_training(mode, level, seed=None, locked=False, playlist=None):
    """Создать тренировку. Возвращает (session, seed).

    seed - зерно генератора заданий: одно зерно даёт одни и те же задания.
    Если его нет - берём случайное. По зерну строится код тренировки,
    который показывается на экране результатов.
    locked=True - тренировка по коду: число заданий фиксировано (чтобы у
    всех, кто ввёл код, было поровну), а уровень менять нельзя.
    playlist - шаг «Моей тренировки» (logic/playlist.py)."""
    session, seed = _make_session(mode, level, seed, locked, playlist)
    session.seed = seed
    global pending_resume
    resume, pending_resume = pending_resume, None
    if resume and playlist is None and resume["mode"] == mode and resume["seed"] == seed:
        restore(session, resume)                    # «Продолжить тренировку»
        session.replay_levels = [r.level for r in session.results]
    if mode == "blitz":
        session.deadline = time.time() + BLITZ_SECONDS
        session.no_hints = True          # подсказка в блице только мешает
    elif locked and session.code in class_limits and class_limits[session.code]:
        session.deadline = time.time() + 60 * class_limits[session.code]
        session.note = f"задание для класса {session.code}"
    # Автосохранение - только у обычных тренировок и тренировок по коду
    if (playlist is None and session.deadline is None
            and getattr(session, "duel", None) is None):
        session.on_record = _autosave
    return session, seed


def task_source(session, factory, seed):
    """Откуда брать задания: сохранённые ошибки (повторение) или генератор
    с зерном. factory(зерно) создаёт генератор режима."""
    items = getattr(session, "review_items", None)
    if items:
        source = ReviewSource(factory, items)
    else:
        source = TrackingSource(factory, seed)
        source.fast_forward(getattr(session, "replay_levels", ()))
    session.source = source
    return source


def time_up(screen):
    """Время тренировки вышло: засчитываем то, что успели решить."""
    session = screen.session
    if session.total == 0:
        screen.navigate("menu")
        return
    session.length = session.total
    finish_training(screen)


def _make_session(mode, level, seed, locked, playlist):
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
        if playlist.stage is not None:  # входной / итоговый тест: одинаковый для всех
            seed = playlist.seeds.get(mode, seed)
            session.no_hints = True
            session.note = "тест  •  без подсказок"
        if getattr(playlist, "review", None):     # «Повторить ошибки»
            session.review_items = playlist.review.get(mode, [])
            session.note = "повторение ошибок"
        if getattr(playlist, "lesson", None) is not None:
            session.note = f"урок {playlist.lesson + 1}"
        return session, seed

    if locked:
        session = TrainingSession(mode, level, CODE_LENGTH[mode],
                                  code=make_code(mode, level, seed), locked=True)
        session.note = f"тренировка по коду {session.code}"
        duel = active_duel
        if duel is not None and not duel.is_done and session.code == duel.code:
            session.duel = duel
            session.note = f"дуэль  •  ходит {duel.current_player['name']}"
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
    if getattr(screen.session, "duel", None) is not None:
        screen.navigate("duel_turn", session=screen.session)     # ход в дуэли окончен
        return
    playlist = screen.playlist
    if playlist is None:
        screen.navigate("results", session=screen.session)
        return
    playlist.finish_step(screen.session)
    if playlist.is_done and playlist.lesson is not None:
        screen.navigate("lesson_results", playlist=playlist)
    elif playlist.is_done and playlist.stage is not None:
        screen.navigate("test_results", playlist=playlist)
    elif playlist.is_done:
        screen.navigate("custom_results", playlist=playlist)
    else:
        mode, _ = playlist.current
        screen.navigate(mode, playlist=playlist)
