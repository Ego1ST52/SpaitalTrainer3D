# Все настройки и цвета проекта в одном месте.

WINDOW_TITLE = "Spatial Trainer 3D"

# Тёмная тема
BACKGROUND = "#0b1220"
FLOOR_COLOR = "#0f1828"
ACCENT = "#22d3ee"
TEXT_COLOR = "#cbd5e1"
CUBE_CORE = "#1b2433"

# Палитра интерфейса (используется в interface/ui_kit.py)
SURFACE = "#121c2e"          # фон карточек и панелей
SURFACE_HOVER = "#192841"    # карточка под курсором
BORDER = "#1f2d45"           # тонкая рамка панелей
ACCENT_DIM = "#0e3a46"       # тёмная подложка под акцентные иконки
TEXT_STRONG = "#f1f5f9"      # заголовки
TEXT_MUTED = "#64748b"       # подписи и подсказки

# Шрифт с кириллицей (путь относительно папки с main.py)
FONT_PATH = "OpenSans-Regular.ttf"

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
BUTTON_COLOR = "#18243a"
BUTTON_HOVER = "#22324d"
SELECTED_COLOR = "#0e7490"
SHOW_FPS = False   # счётчик кадров в углу (для отладки)
# Тренировка
SESSION_LENGTH = 10

LEVEL_NAMES = {"easy": "Начальный", "medium": "Средний", "hard": "Продвинутый"}
MODE_NAMES = {"rotation": "Вращение куба", "matching": "Одинаковые фигуры"}
# База данных
DB_PATH = "data/spatial_trainer.db"
DEFAULT_USER = "Игрок"