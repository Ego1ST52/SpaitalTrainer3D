"""«Повторить ошибки» - интервальное повторение. Без Ursina.

Задание, в котором была ошибка, попадает в список повторения и
возвращается завтра. Если при повторении ответ верный, задание переходит
в следующую «коробку» и возвращается всё реже: через 1, 3, 7 дней.
После третьего верного повторения задание считается выученным и уходит.
Ошибка при повторении - снова в первую коробку, на завтра.
(Так работают карточки Лейтнера, по которым учат слова.)

Элемент списка: {'mode', 'seed', 'levels', 'box', 'due'} - режим, ключ
задания (см. logic/task_source.py), номер коробки и дата следующего повтора.
"""

from datetime import date, timedelta

BOX_DAYS = (1, 3, 7)          # через сколько дней повторять в каждой коробке
MAX_ITEMS = 60                # больше не храним (самые старые уходят)
MAX_PER_REVIEW = 10           # заданий в одной тренировке повторения
SKIP_MODES = ("blitz",)       # блиц - на время, повторять его задания не нужно


def _key(item):
    return item["mode"], item["seed"], tuple(item["levels"])


def update_review(items, mode, outcomes, today=None, reviewing=False):
    """Новый список повторения после тренировки.
    outcomes - [((зерно, уровни), верно ли), ...] по заданиям тренировки.
    reviewing=True - это была тренировка повторения: верные ответы
    продвигают задание по коробкам."""
    if mode in SKIP_MODES:
        return list(items)
    today = today or date.today()
    by_key = {_key(item): dict(item) for item in items}
    for (seed, levels), correct in outcomes:
        key = (mode, seed, tuple(levels))
        if not correct:
            by_key[key] = {"mode": mode, "seed": seed, "levels": list(levels), "box": 0,
                           "due": (today + timedelta(days=BOX_DAYS[0])).isoformat()}
        elif reviewing and key in by_key:
            box = by_key[key]["box"] + 1
            if box >= len(BOX_DAYS):
                del by_key[key]                       # выучено
            else:
                by_key[key]["box"] = box
                by_key[key]["due"] = (today + timedelta(days=BOX_DAYS[box])).isoformat()
    result = list(by_key.values())
    return result[-MAX_ITEMS:]


def due_items(items, today=None):
    """Задания, которые пора повторить (самые давние - первыми)."""
    today = (today or date.today()).isoformat()
    ready = [item for item in items if item["due"] <= today]
    return sorted(ready, key=lambda item: item["due"])[:MAX_PER_REVIEW]


def review_plan(items, mode_order):
    """Шаги тренировки повторения [(режим, сколько)] и {режим: задания}."""
    groups = {}
    for item in items:
        groups.setdefault(item["mode"], []).append(item)
    steps = [(mode, len(groups[mode])) for mode in mode_order if mode in groups]
    return steps, groups


def validate_review(value):
    if not isinstance(value, list):
        raise ValueError("Список повторения должен быть списком")
    for item in value:
        if not isinstance(item, dict) or not {"mode", "seed", "levels", "box",
                                              "due"} <= set(item):
            raise ValueError("Неполный элемент списка повторения")
