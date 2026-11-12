"""Входной и итоговый тест: помогает ли тренажёр? Без Ursina.

Тест - это «Моя тренировка» с постоянным набором: 5 режимов по 3 задания
среднего уровня, без подсказок и без адаптивной сложности. Задания берутся
по постоянным «зёрнам», поэтому у всех игроков тест одинаковый. Входной и
итоговый тест построены одинаково, но задания в них разные - иначе во второй
раз человек просто вспомнил бы ответы.

Итоги каждого теста сохраняются в настройках игрока (prefs "assessment"):
{"pre": {...}, "post": {...}} - потом их можно сравнить.
"""

from datetime import date

from logic.playlist import Playlist

TEST_LEVEL = "medium"
TEST_STEPS = [("rotation", 3), ("matching", 3), ("projection", 3), ("count", 3),
              ("nets", 3)]
# Зёрна заданий: у входного и итогового теста - разные
TEST_SEEDS = {
    "pre": {"rotation": 1101, "matching": 1202, "projection": 1303, "count": 1404,
            "nets": 1505},
    "post": {"rotation": 2101, "matching": 2202, "projection": 2303, "count": 2404,
             "nets": 2505},
}
STAGE_NAMES = {"pre": "Входной тест", "post": "Итоговый тест"}


def make_test(stage):
    """Плейлист теста: stage - 'pre' (входной) или 'post' (итоговый)."""
    if stage not in TEST_SEEDS:
        raise ValueError(f"Неизвестный тест: {stage!r}")
    playlist = Playlist(TEST_STEPS, TEST_LEVEL, adaptive=False)
    playlist.seeds = dict(TEST_SEEDS[stage])
    playlist.stage = stage                 # это тест (а не обычная тренировка)
    return playlist


def summarize_test(playlist, day=None):
    """Итоги теста для сохранения: точность, среднее время, точность по режимам."""
    results = playlist.all_results
    if not results:
        raise ValueError("Тест не пройден")
    modes = {}
    for session in playlist.sessions:
        done = modes.setdefault(session.mode, [0, 0])
        done[0] += session.correct
        done[1] += session.total
    return {
        "date": (day or date.today()).isoformat(),
        "accuracy": round(100 * sum(r.correct for r in results) / len(results), 1),
        "seconds": round(sum(r.seconds for r in results) / len(results), 1),
        "modes": {mode: round(100 * c / t, 1) for mode, (c, t) in modes.items()},
    }


def validate_assessment(value):
    """Проверка сохранённых итогов (для prefs)."""
    if not isinstance(value, dict) or not set(value) <= set(TEST_SEEDS):
        raise ValueError("Итоги тестов должны быть словарём {'pre': ..., 'post': ...}")
    for result in value.values():
        if not isinstance(result, dict) or not {"date", "accuracy", "seconds",
                                                "modes"} <= set(result):
            raise ValueError("Неполные итоги теста")


def compare(pre, post):
    """Строки сравнения: (что, было, стало, изменение-текст, лучше ли).
    Для времени «лучше» - когда стало меньше."""
    rows = [("Точность", f"{pre['accuracy']:.0f}%", f"{post['accuracy']:.0f}%",
             post["accuracy"] - pre["accuracy"], "%", True),
            ("Среднее время", f"{pre['seconds']:.1f} с", f"{post['seconds']:.1f} с",
             post["seconds"] - pre["seconds"], " с", False)]
    result = []
    for name, before, after, delta, unit, more_is_better in rows:
        text = f"{delta:+.0f}{unit}" if unit == "%" else f"{delta:+.1f}{unit}"
        better = delta > 0 if more_is_better else delta < 0
        result.append((name, before, after, text if delta else "без изменений",
                       better if delta else None))
    return result
