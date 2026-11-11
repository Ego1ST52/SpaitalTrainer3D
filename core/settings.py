# Все настройки и цвета проекта в одном месте.

WINDOW_TITLE = "Spatial Trainer 3D"

# Тёмная тема
BACKGROUND = "#070b14"
FLOOR_COLOR = "#0d1524"
ACCENT = "#22d3ee"
TEXT_COLOR = "#cbd5e1"
CUBE_CORE = "#1b2433"

# Фон: радиальное свечение (центр -> края), см. engine/backdrop.py
BACKDROP_GLOW = "#16294a"
BACKDROP_EDGE = "#060912"

# Палитра интерфейса (используется в interface/ui_kit.py)
SURFACE = "#101a2c"          # фон карточек и панелей
SURFACE_ALPHA = 0.82         # панели полупрозрачные («стекло»)
SURFACE_HOVER = "#182844"    # карточка под курсором
BORDER = "#22314a"           # тонкая рамка панелей
EDGE_LIGHT = "#2f4466"       # светлая кромка сверху у панелей
ACCENT_DIM = "#0e3a46"       # тёмная подложка под акцентные иконки
TEXT_STRONG = "#f1f5f9"      # заголовки
TEXT_MUTED = "#64748b"       # подписи и подсказки

# У каждого режима свой цвет: (яркий, тёмная подложка)
MODE_COLORS = {
    "rotation": ("#22d3ee", "#0b3440"),
    "matching": ("#a78bfa", "#2a2150"),
    "projection": ("#fbbf24", "#3d2e0a"),
    "construction": ("#34d399", "#0b3a2c"),
    "custom": ("#f472b6", "#3d1630"),
}

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
# Режимы 2 и 3: фигуры из кубиков
SHAPE_COLOR = "#a78bfa"
SHAPE_HOVER = "#ddd6fe"      # фигура под курсором
PROJECTION_SHAPE_COLOR = "#fbbf24"
# Режим 4: конструирование
BUILD_COLOR = "#34d399"
CONSTRUCTION_LENGTH = 5     # сборка дольше, поэтому заданий в тренировке меньше
CORRECT_COLOR = "#22c55e"
WRONG_COLOR = "#ef4444"
LABEL_SCALE = 40   # размер букв-меток в 3D-сцене (подберите, если мелко/крупно)
# Интерфейс
BUTTON_COLOR = "#18243a"
BUTTON_HOVER = "#22324d"
SELECTED_COLOR = "#0e7490"
SELECTED_HOVER = "#1590ab"   # кнопка главного действия под курсором
NAV_FACE = "#0e1830"         # грани куба-меню
NAV_CORE = "#0a1222"         # «ядро» куба-меню
HUB_COLOR = "#94a3b8"        # грань «Профиль»
SHOW_FPS = False   # счётчик кадров в углу (для отладки)
# Тренировка
SESSION_LENGTH = 10

LEVEL_NAMES = {"easy": "Начальный", "medium": "Средний", "hard": "Продвинутый"}
MODE_NAMES = {"rotation": "Вращение куба", "matching": "Одинаковые фигуры",
              "projection": "Проекции", "construction": "Конструирование",
              "custom": "Моя тренировка"}
# База данных
DB_PATH = "data/spatial_trainer.db"
DEFAULT_USER = "Игрок"