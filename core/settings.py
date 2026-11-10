# Все настройки и цвета проекта в одном месте.

WINDOW_TITLE = "Spatial Trainer 3D"

# Тёмная тема
BACKGROUND = "#0e1621"
FLOOR_COLOR = "#162233"
ACCENT = "#22d3ee"
TEXT_COLOR = "#cbd5e1"
CUBE_CORE = "#1b2433"

# Шрифт с кириллицей (путь относительно папки с main.py)
FONT_PATH = "assets/fonts/arial.ttf"

# Длительность поворота куба, секунд
ROTATION_DURATION = 0.3
# Если поворот на экране идёт в обратную сторону, поменяйте знак нужной оси на -1
AXIS_SIGN = {"x": 1, "y": 1, "z": -1}
# Названия цветов граней куба (используются и логикой, и 3D-кубом)
FACE_COLOR_NAMES = {
    "+X": "красный", "-X": "оранжевый",
    "+Y": "белый", "-Y": "жёлтый",
    "+Z": "синий", "-Z": "зелёный",
}
# Режим 2: фигуры из кубиков
SHAPE_COLOR = "#38bdf8"
CORRECT_COLOR = "#22c55e"
WRONG_COLOR = "#ef4444"
LABEL_SCALE = 40   # размер букв-меток в 3D-сцене (подберите, если мелко/крупно)
# Интерфейс
BUTTON_COLOR = "#1e2a3d"
BUTTON_HOVER = "#2b3e5a"
SELECTED_COLOR = "#0e7490"
SHOW_FPS = True