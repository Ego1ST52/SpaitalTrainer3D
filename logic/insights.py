"""Анализ ошибок: персональные выводы по журналу заданий. Без Ursina.

На вход - список заданий из Database.get_task_log(): у каждого режим,
верно/неверно и метки ('axis:z', 'view:right', 'chose:mirror'...).
Выводы делаем, только если примеров достаточно - чтобы не судить
по одной-двум случайным ошибкам.
"""

from collections import defaultdict
from dataclasses import dataclass

from core import settings

MIN_SAMPLES = 5          # сколько заданий одного типа нужно для вывода
MIN_TOTAL = 10           # сколько всего заданий нужно, чтобы что-то советовать
WEAK_GAP = 15            # на сколько п.п. ниже среднего - уже «слабое место»
STRONG_ACCURACY = 85

# Типичные ошибки: метка выбора -> (режим, текст, совет)
MISTAKES = {
    "chose:mirror": ("matching", "Часто выбираете зеркальную фигуру",
                     "зеркальную копию нельзя получить поворотом - ищите отличие "
                     "в «закрученности» фигуры"),
    "chose:visible_only": ("count", "Считаете только видимые кубики",
                           "под каждым верхним кубиком стоят и нижние, даже если их не видно"),
    "chose:reversed": ("rotation", "Путаете порядок поворотов",
                       "повороты выполняются строго по списку сверху вниз - "
                       "от перестановки результат меняется"),
    "chose:skipped": ("rotation", "Теряете последний поворот",
                      "проговорите каждый поворот и отметьте его, прежде чем отвечать"),
    "chose:inverted": ("rotation", "Крутите куб не в ту сторону",
                       "«+» - против часовой стрелки, если смотреть с конца оси "
                       "(правило правой руки)"),
    "chose:start": ("rotation", "Отвечаете про исходное положение",
                    "сначала мысленно выполните все повороты, потом смотрите на грань"),
    "chose:other_view": ("projection", "Путаете стороны фигуры",
                         "сначала найдите на фигуре подпись нужной стороны и мысленно "
                         "встаньте туда"),
    "chose:mirror_view": ("projection", "Видите вид зеркально",
                     "встаньте на место наблюдателя: что у него справа, то и на картинке "
                     "справа"),
    "chose:rotated_view": ("projection", "Поворачиваете картинку вида",
                      "на видах спереди и справа низ фигуры всегда внизу картинки, "
                      "на виде сверху ближняя к вам сторона - внизу"),
    "chose:rev_reversed": ("reverse", "Путаете порядок поворотов",
                           "сравните кубы после первого поворота: какая грань сдвинулась "
                           "первой"),
    "chose:rev_inverted": ("reverse", "Путаете направление поворота",
                           "«+» - против часовой стрелки, если смотреть с конца оси"),
    "chose:rev_skipped": ("reverse", "Не замечаете последний поворот",
                          "проверьте цепочку целиком: куб «было» должен стать ровно как «стало»"),
    "chose:adjacent": ("nets", "Выбираете соседнюю грань вместо противоположной",
                       "в развёртке напротив - грань через одну клетку в ряду"),
}


def _from_count(value, one, many):
    """«из N ...» по-русски: из 1 поворота, из 21 поворота, из 3 поворотов."""
    n = int(value) if str(value).isdigit() else None
    word = one if n is not None and n % 10 == 1 and n % 100 != 11 else many
    return f"из {value} {word}"


def tag_label(tag):
    """Понятная подпись к метке: 'axis:z' -> 'повороты вокруг оси Z'."""
    kind, _, value = tag.partition(":")
    views = {"front": "спереди", "top": "сверху", "right": "справа", "left": "слева",
             "back": "сзади"}
    if kind == "axis":
        return f"повороты вокруг оси {value.upper()}"
    if kind == "target":
        words = {"+Y": "сверху", "-Z": "спереди", "+X": "справа"}
        return f"вопрос «какая грань {words.get(value, value)}»"
    if kind == "plane":
        return "плоскость симметрии " + ("сбоку" if value == "x" else "спереди")
    if kind == "turn":
        return f"фигура повёрнута на {value}°"
    if kind == "angle":
        return f"повороты на {value}°"
    if kind == "moves":
        return f"задания {_from_count(value, 'поворота', 'поворотов')}"
    if kind == "view":
        return f"вид {views.get(value, value)}"
    if kind == "light":
        return f"свет {views.get(value, value)}"
    if kind == "cubes":
        return f"фигуры {_from_count(value, 'кубика', 'кубиков')}"
    if kind == "sides":
        names = {"3": "треугольники", "4": "четырёхугольники", "5": "пятиугольники",
                 "6": "шестиугольники"}
        return f"сечения-{names.get(value, value)}"
    if kind == "hidden":
        return f"башни со скрытыми кубиками ({value})"
    if kind == "grid":
        return f"сетка {value}×{value}"
    if kind == "type":
        names = {"opposite": "вопрос «что напротив»", "cube": "вопрос «какой кубик»",
                 "sides": "число сторон", "shape": "точное название фигуры"}
        return names.get(value, value)
    if tag == "has_mirror":
        return "задания с зеркальной фигурой"
    return tag


@dataclass(frozen=True)
class Insight:
    kind: str        # 'weak', 'mistake', 'strong' или 'info'
    mode: str        # режим (или '' для общих выводов)
    title: str
    detail: str


def accuracy(results):
    return 100 * sum(r["correct"] for r in results) / len(results) if results else 0.0


def tag_stats(log):
    """{(режим, метка): [задания]} - только «что за задание», без меток выбора."""
    stats = defaultdict(list)
    for task in log:
        for tag in task["tags"]:
            if not tag.startswith("chose:"):
                stats[(task["mode"], tag)].append(task)
    return stats


def weakest_tags(log, limit=8):
    """Самые трудные типы заданий: [(режим, метка, точность, сколько)], от худшего."""
    rows = [(mode, tag, accuracy(tasks), len(tasks))
            for (mode, tag), tasks in tag_stats(log).items() if len(tasks) >= MIN_SAMPLES]
    rows.sort(key=lambda row: (row[2], -row[3]))
    return rows[:limit]


def insights(log):
    """Список выводов, самые важные первыми."""
    if len(log) < MIN_TOTAL:
        return [Insight("info", "", "Пока мало данных",
                        f"Для выводов нужно хотя бы {MIN_TOTAL} заданий - решено "
                        f"{len(log)}. Анализ появится после нескольких тренировок.")]

    by_mode = defaultdict(list)
    for task in log:
        by_mode[task["mode"]].append(task)
    found = []

    # 1. Слабые места: тип заданий заметно хуже среднего по своему режиму
    for (mode, tag), tasks in tag_stats(log).items():
        if len(tasks) < MIN_SAMPLES:
            continue
        mode_accuracy = accuracy(by_mode[mode])
        tag_accuracy = accuracy(tasks)
        if mode_accuracy - tag_accuracy >= WEAK_GAP:
            found.append((mode_accuracy - tag_accuracy, Insight(
                "weak", mode, f"{settings.MODE_NAMES.get(mode, mode)}: {tag_label(tag)}",
                f"верно {tag_accuracy:.0f}% при средних {mode_accuracy:.0f}% в режиме "
                f"({len(tasks)} заданий)")))

    # 2. Типичные ошибки: один и тот же неверный выбор повторяется
    for tag, (mode, title, advice) in MISTAKES.items():
        mistakes = [t for t in by_mode.get(mode, []) if tag in t["tags"]]
        wrong = [t for t in by_mode.get(mode, []) if not t["correct"]]
        if len(mistakes) >= 3 and len(mistakes) >= 0.4 * len(wrong):
            found.append((100, Insight("mistake", mode, title,
                                       f"{len(mistakes)} раз из {len(wrong)} ошибок. "
                                       f"Совет: {advice}.")))

    # 3. Сильные стороны
    for mode, tasks in by_mode.items():
        if len(tasks) >= MIN_TOTAL and accuracy(tasks) >= STRONG_ACCURACY:
            found.append((accuracy(tasks) - 200, Insight(
                "strong", mode, f"Сильная сторона: {settings.MODE_NAMES.get(mode, mode)}",
                f"верно {accuracy(tasks):.0f}% из {len(tasks)} заданий")))

    found.sort(key=lambda item: -item[0])
    result = [insight for _, insight in found]
    if not result:
        result.append(Insight("info", "", "Ровные результаты",
                              "Заметных слабых мест нет: по всем типам заданий "
                              "точность близка к средней."))
    return result


PRACTICE_PER_MODE = 5      # заданий на режим в «Работе над ошибками»
PRACTICE_MODES = 3         # сколько самых трудных режимов взять
PRACTICE_BELOW = 90        # режимы с точностью ниже этой считаем «трудными»


def practice_steps(log):
    """«Работа над ошибками»: шаги тренировки [(режим, заданий)] из самых трудных
    режимов (точность ниже PRACTICE_BELOW%, хотя бы MIN_SAMPLES заданий), от
    самого трудного. Пустой список - трудных режимов нет или данных мало."""
    by_mode = defaultdict(list)
    for task in log or []:
        by_mode[task["mode"]].append(task)
    rows = [(accuracy(tasks), mode) for mode, tasks in by_mode.items()
            if len(tasks) >= MIN_SAMPLES and accuracy(tasks) < PRACTICE_BELOW]
    rows.sort()
    return [(mode, PRACTICE_PER_MODE) for _, mode in rows[:PRACTICE_MODES]]
