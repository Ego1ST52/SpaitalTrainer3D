"""Таблица рекордов игроков на этом компьютере. Без Ursina.

players - [(имя, история тренировок)], история - как из Database.get_history().
Место определяет рекорд - больше всего баллов за одну тренировку; при равенстве
выше тот, у кого лучше общая точность.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    place: int
    name: str
    best: int             # рекорд: баллы за одну тренировку
    accuracy: float       # общая точность, %
    trainings: int
    total: int            # баллов за всё время


def leaderboard(players, mode=None):
    """Строки таблицы (только игроки, у которых есть тренировки в этом режиме)."""
    rows = []
    for name, history in players:
        games = [h for h in history or [] if mode is None or h["mode"] == mode]
        if not games:
            continue
        tasks = sum(g["tasks_total"] for g in games)
        correct = sum(g["tasks_correct"] for g in games)
        rows.append((max(g["points"] for g in games),
                     100 * correct / tasks if tasks else 0.0,
                     len(games), sum(g["points"] for g in games), name))
    rows.sort(key=lambda r: (-r[0], -r[1], r[4]))
    return [Row(place, name, best, accuracy, trainings, total)
            for place, (best, accuracy, trainings, total, name) in enumerate(rows, start=1)]
