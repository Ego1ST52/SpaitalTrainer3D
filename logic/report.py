"""Отчёт для учителя: таблица по всем игрокам (CSV для Excel). Без Ursina.

Разделитель «;» и кодировка UTF-8 с меткой BOM - так русский Excel
открывает файл сразу, двойным щелчком, без «кракозябр».
"""

import csv
from datetime import date, datetime
from pathlib import Path

from core import settings
from data.statistics import summarize
from logic.insights import insights
from logic.playlist import MODE_ORDER


def player_row(name, history, log):
    """Строка отчёта об одном игроке (словарь «столбец -> значение»)."""
    stats = summarize(history) if history else None
    row = {
        "Игрок": name,
        "Тренировок": len(history),
        "Заданий": stats["tasks"] if stats else 0,
        "Точность, %": round(stats["accuracy"]) if stats else "",
        "Баллы": stats["points"] if stats else 0,
        "Последняя тренировка": (datetime.fromisoformat(history[0]["played_at"])
                                 .strftime("%d.%m.%Y") if history else ""),
    }
    for mode in MODE_ORDER:
        games = [h for h in history if h["mode"] == mode]
        total = sum(h["tasks_total"] for h in games)
        correct = sum(h["tasks_correct"] for h in games)
        row[f"{settings.MODE_NAMES[mode]}, %"] = round(100 * correct / total) if total else ""
    found = insights(log) if log else []
    weak = next((i for i in found if i.kind in ("weak", "mistake")), None)
    strong = next((i for i in found if i.kind == "strong"), None)
    row["Слабое место"] = weak.title if weak else ""
    row["Сильная сторона"] = strong.title.replace("Сильная сторона: ", "") if strong else ""
    return row


def build_rows(players):
    """players - [(имя, история, журнал заданий)] -> строки отчёта."""
    return [player_row(name, history, log) for name, history, log in players]


def write_csv(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    return path


def report_path(folder=None):
    folder = Path(folder) if folder else Path.home() / "Documents" / "SpatialTrainer3D"
    return folder / f"отчёт_{date.today():%Y-%m-%d}.csv"
