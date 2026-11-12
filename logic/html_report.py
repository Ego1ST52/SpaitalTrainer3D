"""Отчёт одной страницей (HTML) с графиками - для учителя или для защиты.
Без Ursina - проверяется автотестами.

Страница самодостаточная: стили и графики (SVG) внутри файла, интернет не
нужен. Её можно открыть в любом браузере и распечатать (Ctrl+P).
"""

from datetime import date
from html import escape
from pathlib import Path

from core import settings
from data.statistics import summarize
from logic.assessment import STAGE_NAMES, compare
from logic.experiment import angle_table, conclusion, experiment_points
from logic.insights import insights
from logic.playlist import MODE_ORDER

CHART_TRAININGS = 15       # сколько последних тренировок на графике

STYLE = """
:root { color-scheme: light; }      /* отчёт всегда светлый: так его удобно печатать */
html { background: #ffffff; }
body { background: #ffffff; font-family: "Segoe UI", Arial, sans-serif; color: #1e293b; max-width: 960px;
       margin: 32px auto; padding: 0 16px; line-height: 1.45; }
h1 { margin-bottom: 0; } .muted { color: #64748b; }
h2 { border-bottom: 2px solid #22d3ee; padding-bottom: 4px; margin-top: 40px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th, td { border-bottom: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; }
th { background: #f1f5f9; font-weight: 600; }
td.num, th.num { text-align: right; }
.cards { display: flex; gap: 12px; flex-wrap: wrap; }
.card { flex: 1 1 160px; background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 10px 14px; }
.card b { display: block; font-size: 24px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 14px; color: #475569; }
.key i { display: inline-block; width: 12px; height: 12px; border-radius: 3px;
         margin-right: 6px; vertical-align: -1px; }
.good { color: #16a34a; } .bad { color: #dc2626; }
@media print { h2 { break-after: avoid; } section { break-inside: avoid; } }
"""


def _accuracy(game):
    return 100 * game["tasks_correct"] / game["tasks_total"] if game["tasks_total"] else 0


def accuracy_chart(history):
    """SVG-столбики точности по последним тренировкам (старые слева)."""
    games = list(reversed(history[:CHART_TRAININGS]))
    if not games:
        return '<p class="muted">Тренировок пока нет.</p>'
    width, height, gap = 640, 160, 6
    bar = (width - gap * (len(games) - 1)) / len(games)
    parts = [f'<svg viewBox="0 0 {width} {height + 24}" width="100%" '
             'role="img" aria-label="Точность по тренировкам">']
    for line in (50, 100):
        y = height - height * line / 100
        parts.append(f'<line x1="0" x2="{width}" y1="{y:.1f}" y2="{y:.1f}" '
                     'stroke="#e2e8f0" stroke-dasharray="4 4"/>')
    for i, game in enumerate(games):
        value = _accuracy(game)
        x = i * (bar + gap)
        h = max(2, height * value / 100)
        colour = settings.MODE_COLORS.get(game["mode"], ("#22d3ee",))[0]
        name = escape(settings.MODE_NAMES.get(game["mode"], game["mode"]))
        parts.append(f'<rect x="{x:.1f}" y="{height - h:.1f}" width="{bar:.1f}" '
                     f'height="{h:.1f}" rx="3" fill="{colour}"><title>{name}: '
                     f'{value:.0f}%</title></rect>')
        parts.append(f'<text x="{x + bar / 2:.1f}" y="{height + 16}" font-size="11" '
                     f'text-anchor="middle" fill="#64748b">{value:.0f}</text>')
    parts.append("</svg>")
    # Подписи цветов: какой цвет - какой режим (только режимы с графика)
    modes = [m for m in MODE_ORDER if any(g["mode"] == m for g in games)]
    legend = "".join(
        f'<span class="key"><i style="background:{settings.MODE_COLORS[m][0]}"></i>'
        f"{escape(settings.MODE_NAMES[m])}</span>" for m in modes)
    return "".join(parts) + f'<p class="legend">{legend}</p>'



def _modes_table(history):
    rows = []
    for mode in MODE_ORDER:
        games = [h for h in history if h["mode"] == mode]
        if not games:
            continue
        total = sum(g["tasks_total"] for g in games)
        correct = sum(g["tasks_correct"] for g in games)
        best = max(g["points"] for g in games)
        rows.append(f"<tr><td>{escape(settings.MODE_NAMES[mode])}</td>"
                    f'<td class="num">{len(games)}</td>'
                    f'<td class="num">{100 * correct / total:.0f}%</td>'
                    f'<td class="num">{best}</td></tr>')
    if not rows:
        return ""
    return ('<table><tr><th>Режим</th><th class="num">Тренировок</th>'
            '<th class="num">Точность</th><th class="num">Рекорд, баллов</th></tr>'
            + "".join(rows) + "</table>")


def _tests_block(assessment):
    pre, post = (assessment or {}).get("pre"), (assessment or {}).get("post")
    if not pre:
        return '<p class="muted">Входной тест ещё не пройден.</p>'
    if not post:
        return (f"<p>{STAGE_NAMES['pre']} ({escape(pre['date'])}): точность "
                f"{pre['accuracy']:.0f}%, среднее время {pre['seconds']:.1f} с. "
                "Итоговый тест ещё не пройден.</p>")
    rows = []
    for name, before, after, delta, better in compare(pre, post):
        cls = "" if better is None else (' class="good"' if better else ' class="bad"')
        rows.append(f'<tr><td>{name}</td><td class="num">{before}</td>'
                    f'<td class="num">{after}</td><td class="num"><span{cls}>{delta}'
                    "</span></td></tr>")
    return (f'<p class="muted">Входной тест - {escape(pre["date"])}, итоговый - '
            f'{escape(post["date"])}.</p><table><tr><th></th><th class="num">До</th>'
            '<th class="num">После</th><th class="num">Изменение</th></tr>'
            + "".join(rows) + "</table>")


def _experiment_block(log):
    points = experiment_points(log)
    table = angle_table(points)
    cells = "".join(f'<td class="num">{table[a][1]:.1f} с<br><span class="muted">'
                    f"{table[a][0]} отв.</span></td>" if a in table else
                    '<td class="num muted">-</td>' for a in (0, 90, 120, 180))
    return ('<table><tr><th>Угол поворота</th><th class="num">0°</th><th class="num">90°'
            '</th><th class="num">120°</th><th class="num">180°</th></tr>'
            f"<tr><td>Среднее время ответа</td>{cells}</tr></table>"
            f"<p>{escape(conclusion(points))}</p>")


def player_section(name, history, log, assessment):
    stats = summarize(history) if history else None
    cards = ""
    if stats:
        cards = ('<div class="cards">'
                 f'<div class="card">Тренировок<b>{len(history)}</b></div>'
                 f'<div class="card">Заданий<b>{stats["tasks"]}</b></div>'
                 f'<div class="card">Точность<b>{stats["accuracy"]:.0f}%</b></div>'
                 f'<div class="card">Баллы<b>{stats["points"]}</b></div></div>')
    found = insights(log) if log else []
    advice = "".join(f"<li><b>{escape(i.title)}</b> - {escape(i.detail)}</li>"
                     for i in found[:4])
    return (f"<section><h2>{escape(name)}</h2>{cards}"
            "<h3>Точность по последним тренировкам</h3>" + accuracy_chart(history) +
            "<h3>По режимам</h3>" + (_modes_table(history) or
                                     '<p class="muted">Нет данных.</p>') +
            "<h3>Тест до и после</h3>" + _tests_block(assessment) +
            "<h3>Опыт «время против угла поворота»</h3>" + _experiment_block(log) +
            ("<h3>Выводы</h3><ul>" + advice + "</ul>" if advice else "") + "</section>")


def build_html(players, today=None):
    """players - [(имя, история, журнал заданий, итоги тестов)] -> текст страницы."""
    today = today or date.today()
    sections = "".join(player_section(*player) for player in players)
    return ("<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>Отчёт Spatial Trainer 3D</title><style>{STYLE}</style></head><body>"
            "<h1>Spatial Trainer 3D - отчёт</h1>"
            f'<p class="muted">Составлен {today:%d.%m.%Y}. Игроков: {len(players)}. '
            "Показатели отражают результаты в игре и не доказывают изменения "
            "когнитивных способностей.</p>" + sections + "</body></html>")


def write_html(text, folder=None, today=None):
    folder = Path(folder) if folder else Path.home() / "Documents" / "SpatialTrainer3D"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"отчёт_{(today or date.today()):%Y-%m-%d}.html"
    path.write_text(text, encoding="utf-8")
    return path

