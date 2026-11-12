from logic.insights import MIN_TOTAL, insights, tag_label, weakest_tags


def task(mode, correct, *tags):
    return {"mode": mode, "level": "easy", "correct": correct, "seconds": 5.0,
            "played_at": "2026-11-12T10:00:00", "tags": list(tags)}


def test_too_little_data():
    result = insights([task("rotation", True, "axis:x")] * 3)
    assert len(result) == 1 and result[0].kind == "info" and "мало данных" in result[0].title


def test_weak_axis_is_found():
    log = ([task("rotation", True, "axis:x")] * 10 + [task("rotation", True, "axis:y")] * 10
           + [task("rotation", False, "axis:z")] * 4 + [task("rotation", True, "axis:z")] * 2)
    weak = [i for i in insights(log) if i.kind == "weak"]
    assert weak and "оси Z" in weak[0].title
    assert "33%" in weak[0].detail                     # 2 из 6 верно


def test_no_conclusion_from_few_samples():
    # Ось Z плохая, но всего 3 примера - выводов не делаем
    log = [task("rotation", True, "axis:x")] * 12 + [task("rotation", False, "axis:z")] * 3
    assert not [i for i in insights(log) if i.kind == "weak"]


def test_mirror_mistake_pattern():
    log = ([task("matching", True, "cubes:5")] * 8
           + [task("matching", False, "cubes:5", "chose:mirror")] * 4
           + [task("matching", False, "cubes:5", "chose:changed")])
    mistakes = [i for i in insights(log) if i.kind == "mistake"]
    assert mistakes and "зеркальную" in mistakes[0].title
    assert "Совет" in mistakes[0].detail


def test_strength_and_even_results():
    log = [task("projection", True, "view:top")] * 12
    result = insights(log)
    assert result[0].kind == "strong" and "Проекции" in result[0].title
    even = [task("rotation", i % 2 == 0, "axis:x") for i in range(12)]
    assert insights(even)[0].kind == "info"           # 50% и без перекосов


def test_weakest_tags_sorted():
    log = ([task("rotation", True, "axis:x")] * 5 + [task("rotation", False, "axis:z")] * 5
           + [task("projection", True, "view:top")] * 3)     # мало примеров - не попадёт
    rows = weakest_tags(log)
    assert rows[0][:2] == ("rotation", "axis:z") and rows[0][2] == 0
    assert all(row[3] >= 5 for row in rows)


def test_tag_labels():
    assert tag_label("axis:z") == "повороты вокруг оси Z"
    assert tag_label("view:right") == "вид справа"
    assert tag_label("light:left") == "свет слева"
    assert tag_label("sides:6") == "сечения-шестиугольники"
    assert tag_label("type:cube") == "вопрос «какой кубик»"
    assert tag_label("unknown:1") == "unknown:1"
    assert MIN_TOTAL >= 10


def test_labels_agree_with_numbers():
    assert tag_label("moves:1") == "задания из 1 поворота"
    assert tag_label("moves:3") == "задания из 3 поворотов"
    assert tag_label("moves:11") == "задания из 11 поворотов"
    assert tag_label("cubes:21") == "фигуры из 21 кубика"
