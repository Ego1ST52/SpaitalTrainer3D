import csv

from core import settings
from logic.report import build_rows, report_path, write_csv


def game(mode, total, correct, day=10):
    return {"mode": mode, "level": "easy", "played_at": f"2026-11-{day:02d}T10:00:00",
            "tasks_total": total, "tasks_correct": correct, "points": 50 * correct,
            "total_seconds": 60.0, "code": None}


def task(mode, correct, tag):
    return {"mode": mode, "level": "easy", "correct": correct, "seconds": 3,
            "played_at": "2026-11-10T10:00:00", "tags": [tag]}


def test_rows_per_player():
    anya_history = [game("rotation", 10, 9, day=12), game("projection", 10, 5)]
    anya_log = ([task("rotation", True, "axis:x")] * 10
                + [task("rotation", False, "axis:z")] * 4 + [task("rotation", True, "axis:z")])
    rows = build_rows([("Аня", anya_history, anya_log), ("Борис", [], [])])
    anya, boris = rows
    assert anya["Игрок"] == "Аня" and anya["Тренировок"] == 2 and anya["Заданий"] == 20
    assert anya["Точность, %"] == 70
    assert anya[f"{settings.MODE_NAMES['rotation']}, %"] == 90
    assert anya[f"{settings.MODE_NAMES['matching']}, %"] == ""      # не играла
    assert anya["Последняя тренировка"] == "12.11.2026"
    assert "оси Z" in anya["Слабое место"]
    assert boris["Тренировок"] == 0 and boris["Точность, %"] == ""
    assert list(anya) == list(boris)                                  # одинаковые столбцы


def test_csv_opens_in_excel_style(tmp_path):
    rows = build_rows([("Аня", [game("rotation", 10, 9)], [])])
    path = write_csv(rows, report_path(tmp_path))
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")                            # метка UTF-8 для Excel
    with open(path, encoding="utf-8-sig", newline="") as file:
        table = list(csv.reader(file, delimiter=";"))
    assert table[0][0] == "Игрок" and table[1][0] == "Аня"
    assert path.name.startswith("отчёт_") and path.suffix == ".csv"
