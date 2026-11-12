"""Опыт «Время против угла поворота». Без Ursina.

Известный опыт психологов Шепарда и Метцлер (1971): люди сравнивают
две фигуры, мысленно поворачивая одну из них. Поэтому чем больше угол
между фигурами, тем дольше ответ - время растёт почти по прямой.

Здесь опыт повторяется на ваших ответах в режиме «Одинаковые фигуры»:
у каждого задания есть метка turn:<угол> (насколько правильный вариант
повёрнут относительно образца). Берём только верные ответы без подсказок
и считаем среднее время для каждого угла и наклон прямой (секунд на 90°).
"""

ANGLES = (0, 90, 120, 180)
MIN_ANSWERS = 12          # меньше - выводы делать рано
MAX_SECONDS = 120         # ответы дольше двух минут - игрок отвлёкся, не считаем


def experiment_points(task_log):
    """[(угол, секунды)] - верные ответы «Одинаковых фигур» без подсказок."""
    points = []
    for entry in task_log or []:
        if entry["mode"] != "matching" or not entry["correct"]:
            continue
        tags = entry["tags"]
        if "hint" in tags or entry["seconds"] > MAX_SECONDS:
            continue
        for tag in tags:
            if tag.startswith("turn:"):
                points.append((int(tag[5:]), entry["seconds"]))
    return points


def angle_table(points):
    """{угол: (сколько ответов, среднее время)} для углов, где есть ответы."""
    table = {}
    for angle in ANGLES:
        times = [s for a, s in points if a == angle]
        if times:
            table[angle] = (len(times), sum(times) / len(times))
    return table


def trend(points):
    """Прямая «время = a + b·угол» методом наименьших квадратов.
    Возвращает (a, b) или None, если углы все одинаковые."""
    if len(points) < 2:
        return None
    n = len(points)
    mean_x = sum(a for a, _ in points) / n
    mean_y = sum(s for _, s in points) / n
    spread = sum((a - mean_x) ** 2 for a, _ in points)
    if spread == 0:
        return None
    slope = sum((a - mean_x) * (s - mean_y) for a, s in points) / spread
    return mean_y - slope * mean_x, slope


def conclusion(points):
    """Вывод простыми словами."""
    if len(points) < MIN_ANSWERS:
        return (f"Пока мало данных: {len(points)} из {MIN_ANSWERS} верных ответов. "
                "Пройдите тренировку «Одинаковые фигуры».")
    line = trend(points)
    if line is None:
        return "Все задания были с одним углом - сравнить пока не с чем."
    per_quarter = line[1] * 90
    if per_quarter > 0.3:
        return (f"Эффект есть: каждые 90° поворота добавляют вам около "
                f"{per_quarter:.1f} с. Вы действительно поворачиваете фигуру в уме.")
    if per_quarter < -0.3:
        return ("Странно: при большом угле вы отвечаете быстрее. Наберите больше "
                "ответов - возможно, это случайность.")
    return ("Время почти не зависит от угла - вы узнаёте фигуры, не поворачивая их "
            "в уме (или данных пока мало).")
