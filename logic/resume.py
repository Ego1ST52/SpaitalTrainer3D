"""«Продолжить тренировку»: недоигранная тренировка сохраняется после каждого
ответа и восстанавливается при следующем запуске. Без Ursina.

Сохраняем не сами задания, а то, из чего они получаются: режим, зерно и
уровни уже пройденных заданий. Генератор с тем же зерном выдаст их заново
(см. logic/task_source.py), а результаты ответов вернутся в тренировку.
"""

from logic.session import TaskResult


def snapshot(session):
    """Что сохранить о тренировке (словарь для настроек игрока)."""
    return {
        "mode": session.mode,
        "level": session.level,
        "seed": session.seed,
        "code": session.code,
        "locked": session.locked,
        "length": session.length,
        "adaptive": session.adaptive.level if session.adaptive else None,
        "results": [[r.correct, round(r.seconds, 2), r.points, r.level, list(r.tags)]
                    for r in session.results],
    }


def restore(session, data):
    """Вернуть в новую тренировку результаты сохранённой."""
    session.results = [TaskResult(bool(c), float(s), int(p), level, tuple(tags))
                       for c, s, p, level, tags in data["results"]]
    if session.adaptive and data.get("adaptive"):
        session.adaptive.level = data["adaptive"]


def describe(data, mode_names):
    """Подпись для кнопки: 'Вращение куба, 4 из 10'."""
    return (f"{mode_names.get(data['mode'], data['mode'])}, "
            f"{len(data['results'])} из {data['length']}")


def validate_resume(value):
    if value is None:
        return
    if not isinstance(value, dict) or not {"mode", "level", "seed", "length",
                                           "results"} <= set(value):
        raise ValueError("Неполная сохранённая тренировка")
    if not value["results"]:
        raise ValueError("В сохранённой тренировке нет ответов")
