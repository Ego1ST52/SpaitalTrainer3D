"""«Задание для класса»: учитель создаёт код тренировки с ограничением по
времени, ученики по очереди решают его на этом компьютере (каждый в своём
профиле), а потом учитель видит общую таблицу. Без Ursina.

Задание - это обычный код тренировки (logic/training_code.py), поэтому все
получают одни и те же задания. Ограничение по времени хранится в базе
(app_state 'class_tasks') и работает на этом компьютере.
"""

import random
from datetime import datetime

from logic.training_code import make_code, random_seed

TIME_LIMITS = (0, 5, 10, 15)      # минут; 0 - без ограничения
MAX_TASKS = 20                    # сколько заданий помнить


def make_assignment(mode, level, minutes, rng=random, now=None):
    if minutes not in TIME_LIMITS:
        raise ValueError("Неверное ограничение по времени")
    return {"code": make_code(mode, level, random_seed(rng)), "mode": mode, "level": level,
            "minutes": minutes,
            "created": (now or datetime.now()).isoformat(timespec="minutes")}


def add_assignment(assignments, assignment):
    """Новое задание - первым в списке; старые сверх MAX_TASKS забываются."""
    rest = [a for a in assignments if a["code"] != assignment["code"]]
    return ([assignment] + rest)[:MAX_TASKS]


def limits(assignments):
    """{код: минут} - для тренировок по коду (interface/game_common.py)."""
    return {a["code"]: a["minutes"] for a in assignments}


def results_for(code, players):
    """Таблица по заданию: для каждого игрока - ПЕРВАЯ попытка с этим кодом
    (так честно: все решали одинаковое задание по одному разу).
    players - [(имя, история)]. Возвращает строки-словари, лучшие сверху."""
    rows = []
    for name, history in players:
        tries = [h for h in history or [] if h.get("code") == code]
        if not tries:
            continue
        first = min(tries, key=lambda h: h["played_at"])
        total = first["tasks_total"]
        rows.append({
            "Игрок": name,
            "Верно": first["tasks_correct"],
            "Заданий": total,
            "Точность, %": round(100 * first["tasks_correct"] / total) if total else 0,
            "Баллы": first["points"],
            "Время, с": round(first["total_seconds"]),
            "Когда": datetime.fromisoformat(first["played_at"]).strftime("%d.%m %H:%M"),
            "Попыток": len(tries),
        })
    rows.sort(key=lambda r: (-r["Верно"], -r["Баллы"], r["Время, с"]))
    return rows
