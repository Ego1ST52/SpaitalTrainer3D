"""Расчёт показателей по истории тренировок. Без Ursina и без базы:
на вход - список словарей из Database.get_history() (новые первыми)."""


def summarize(history):
    sessions = len(history)
    tasks = sum(h["tasks_total"] for h in history)
    correct = sum(h["tasks_correct"] for h in history)
    seconds = sum(h["total_seconds"] for h in history)
    return {
        "sessions": sessions,
        "tasks": tasks,
        "correct": correct,
        "accuracy": 100 * correct / tasks if tasks else 0.0,
        "points": sum(h["points"] for h in history),
        "best_points": max((h["points"] for h in history), default=0),
        "average_seconds": seconds / tasks if tasks else 0.0,
    }


def accuracy_of(entry):
    """Точность одной тренировки в процентах."""
    return 100 * entry["tasks_correct"] / entry["tasks_total"] if entry["tasks_total"] else 0.0


def filter_history(history, mode=None, level=None):
    """Оставить тренировки нужного режима и/или уровня (None = любые)."""
    return [h for h in history
            if (mode is None or h["mode"] == mode)
            and (level is None or h["level"] == level)]


def progress_series(history, limit=12):
    """Точность последних limit тренировок в хронологическом порядке
    (старые первыми, чтобы график шёл слева направо)."""
    return [accuracy_of(h) for h in reversed(history[:limit])]


def compare_recent(history, recent_count=3):
    """Сравнить точность последних recent_count тренировок со всеми более ранними.
    None, если тренировок не больше recent_count (сравнивать не с чем)."""
    if len(history) <= recent_count:
        return None
    recent = history[:recent_count]
    earlier = history[recent_count:]
    recent_accuracy = sum(accuracy_of(h) for h in recent) / len(recent)
    earlier_accuracy = sum(accuracy_of(h) for h in earlier) / len(earlier)
    return {
        "recent_count": len(recent),
        "earlier_count": len(earlier),
        "recent_accuracy": recent_accuracy,
        "earlier_accuracy": earlier_accuracy,
        "difference": recent_accuracy - earlier_accuracy,
    }