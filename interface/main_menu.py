"""Главное меню «Куб-навигатор»: меню - это огромный куб, каждая грань - режим.
Поворачиваешь куб стрелками или мышью, лицевая грань светится, клик или Enter -
камера «влетает» в грань и открывается режим. Само меню - маленькое упражнение
на пространственное мышление: нужно помнить, где на кубе какой режим.
"""

from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from core.preferences import prefs
from data.statistics import accuracy_of, filter_history, summarize
from engine.backdrop import FloatingCubes
from engine.nav_cube import mouse_position, NavCube, SIZE
from engine.objects import dispose
from interface.base_screen import BaseScreen
from interface.code_dialog import CodeDialog
from interface.ui_kit import (_draw_icon, Avatar, FRONT, label, LogoMark, mode_color,
                              mode_dim, Panel, PlayerChip, rounded_quad, Segmented, UIButton,
                              with_alpha)
from logic.cube_nav import CubeNavigator, FACE_CONTENT

LEVELS = [("easy", "Начальный"), ("medium", "Средний"), ("hard", "Продвинутый")]

# Что написано на гранях: (номер, название, описание)
FACE_TEXT = {
    "rotation": ("01", "Вращение куба", "какая грань окажется сверху"),
    "matching": ("02", "Одинаковые фигуры", "найдите фигуру после поворота"),
    "projection": ("03", "Проекции", "как фигура выглядит с разных сторон"),
    "construction": ("04", "Конструирование", "соберите фигуру по образцу"),
    "custom": ("05", "Моя тренировка", "несколько режимов подряд"),
    "hub": ("", "Профиль", ""),
}
HUB_COLOR = "#94a3b8"
KEYS = {"left arrow": "left", "right arrow": "right", "up arrow": "up", "down arrow": "down",
        "a": "left", "d": "right", "w": "up", "s": "down"}
FLY_SECONDS = 0.32


def face_color(content):
    return HUB_COLOR if content == "hub" else mode_color(content)


def trainings_text(count):
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} тренировка"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return f"{count} тренировки"
    return f"{count} тренировок"


class MainMenu(BaseScreen):
    """history - тренировки текущего игрока (или None), player - {"name", "color"}."""

    # Между заходами в меню помним сложность и то, какой гранью был повёрнут куб,
    # поэтому после тренировки камера «вылетает» из той же грани.
    remembered_level = "easy"
    remembered_nav = (0, 0)
    remembered_turns = 0

    def __init__(self, manager, history=None, player=None):
        super().__init__(manager)
        self.level = MainMenu.remembered_level
        self.history = history or []
        self.player = player or {"name": settings.DEFAULT_USER, "color": settings.ACCENT}
        self.nav = CubeNavigator(*MainMenu.remembered_nav)
        self.dialog = None
        self.entering = False
        self.drag_start = None
        self.net_cells = {}
        self.borders = {}

        self.own(FloatingCubes())
        self.cube = self.own(NavCube(yaw=MainMenu.remembered_turns, pitch=self.nav.pitch,
                                     position=(0, 0.45, 0)))
        for face in FACE_CONTENT:
            self._build_face(face)
        # Мягкое свечение под кубом в цвете лицевой грани
        self.glow = self.own(Entity(model="circle", rotation_x=90, scale=(5.5, 5.5),
                                    position=(0, -SIZE / 2 - 0.6, 0.5), shader=unlit_shader))

        self._build_overlay()
        self._refresh()

        # «Вылет» из грани: камера стартует у самой грани и отъезжает назад
        if not prefs.reduce_motion:
            camera.z = -SIZE * 0.9

    # ---------- грани ----------
    def _build_face(self, face):
        content = self.cube.contents[face]
        kind = FACE_CONTENT[face]
        accent = face_color(kind)
        half = 0.19                     # грань в «единицах интерфейса»: от -0.19 до 0.19
        # Фон грани с коллайдером: по нему кликают мышью
        bg = Entity(parent=content, model=rounded_quad(2 * half, 2 * half, 0.02),
                    scale=2 * half, color=color.hex("#0e1830"), shader=unlit_shader,
                    collider="box", z=0.003)
        bg.face_name = face
        border = Entity(parent=content, model=rounded_quad(2 * half, 2 * half, 0.02, True),
                        scale=2 * half, shader=unlit_shader, z=0.002)
        self.borders[face] = border
        # Светящийся уголок в цвете режима
        Entity(parent=content, model="quad", shader=unlit_shader, color=color.hex(accent),
               position=(-half + 0.045, half - 0.012, FRONT), scale=(0.07, 0.006))

        number, title, subtitle = FACE_TEXT[kind]
        if kind == "hub":
            self._build_hub(content)
            return
        label(number, (-half + 0.02, half - 0.035), 0.9, accent, parent=content)
        Panel(0.1, 0.1, position=(0, 0.07, FRONT / 2), fill=mode_dim(kind), border=None,
              radius=0.02, alpha=1, parent=content)
        icon = Entity(parent=content, position=(0, 0.07), scale=1.6)
        _draw_icon(kind, icon, accent)
        label(title, (0, -0.025), 1.35 if len(title) < 15 else 1.15, "strong",
              origin=(0, 0), parent=content)
        label(subtitle, (0, -0.07), 0.8, "muted", origin=(0, 0), parent=content)
        label(self._face_stat(kind), (0, -0.14), 0.75, accent, origin=(0, 0), parent=content)

    def _face_stat(self, kind):
        """Короткая строка о ваших результатах в этом режиме."""
        if kind == "custom":
            plan = prefs.get("custom_plan")
            return f"режимов в наборе: {len(plan['modes'])}"
        games = filter_history(self.history, kind)
        if not games:
            return "ещё не пробовали"
        best = max(accuracy_of(g) for g in games)
        return f"рекорд {best:.0f}%  •  {trainings_text(len(games))}"

    def _build_hub(self, content):
        """Нижняя грань «Профиль»: игрок и кнопки статистики, настроек, игроков."""
        name, hex_color = self.player["name"], self.player["color"]
        Avatar(name, hex_color, (0, 0.11, FRONT), size=0.07, parent=content)
        label(name, (0, 0.05), 1.3, "strong", origin=(0, 0), parent=content)
        total = summarize(self.history)["accuracy"] if self.history else None
        label(f"точность за всё время {total:.0f}%" if total is not None else "профиль игрока",
              (0, 0.015), 0.8, "muted", origin=(0, 0), parent=content)
        buttons = [("Статистика", "statistics"), ("Настройки", "settings"),
                   ("Игроки", "profiles")]
        for i, (text, screen) in enumerate(buttons):
            button = UIButton(text, lambda s=screen: self._hub_action(s), parent=content,
                              position=(0, -0.04 - i * 0.047, FRONT), scale=(0.25, 0.04),
                              text_size=0.8)
            button.face_name = "bottom"
            # Ursina считает размер текста кнопки для слоя интерфейса; на грани
            # (она увеличена в CONTENT_SCALE раз) пересчитываем его по масштабу грани
            button.text_entity.world_scale = Vec3(content.world_scale_x * 0.8)

    def _hub_action(self, screen):
        # Кнопки на грани работают, только когда грань «Профиль» перед игроком
        if self.nav.front_content == "hub" and not self.entering and self.dialog is None:
            self.navigate(screen)

    # ---------- интерфейс вокруг куба ----------
    def _build_overlay(self):
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05
        self.own(LogoMark((left + 0.022, 0.43)))
        self.own(label("Spatial Trainer 3D", (left + 0.055, 0.438), 1.4, "strong"))
        self.own(label("тренажёр пространственного мышления", (left + 0.055, 0.405), 0.75,
                       "muted"))
        self.own(PlayerChip(self.player["name"], self.player["color"],
                            lambda: self.navigate("profiles"),
                            position=(right - 0.16, 0.42)))

        # Стрелки вокруг куба (символ › повёрнут в нужную сторону)
        for direction, position, angle in (("left", (-0.34, 0.04), 180),
                                           ("right", (0.37, 0.04), 0),
                                           ("up", (0, 0.335), -90),
                                           ("down", (0, -0.265), 90)):
            holder = self.own(Entity(parent=camera.ui, position=position))
            UIButton("", lambda d=direction: self.turn(d), parent=holder,
                     scale=(0.065, 0.065), radius=0.5, variant="ghost")
            arrow = label("›", (0, 0.003), 2.2, "text", origin=(0, 0), parent=holder)
            arrow.rotation_z = angle

        self.hint = self.own(label("", (0, -0.37), 0.8, "muted", origin=(0, 0)))
        self.level_switch = self.own(Segmented(LEVELS, self.level, self.set_level,
                                               position=(0, -0.445), width=0.5, height=0.05,
                                               text_size=0.75))
        self._build_net()
        self.own(UIButton("По коду", self.open_code_dialog, position=(right - 0.2, -0.445),
                          scale=(0.14, 0.05), text_size=0.8))
        self.own(UIButton("Выход", application.quit, variant="ghost",
                          position=(right - 0.06, -0.445), scale=(0.11, 0.05), text_size=0.8))

    def _build_net(self):
        """Развёртка куба в углу: где вы сейчас; клик по клетке - туда."""
        cell, gap = 0.042, 0.005
        origin_x = window.bottom_left.x + 0.1
        origin_y = -0.39
        layout = {"top": (1, 1), "left": (0, 0), "front": (1, 0), "right": (2, 0),
                  "back": (3, 0), "bottom": (1, -1)}
        self.own(label("развёртка куба", (origin_x - cell / 2,
                                          origin_y + 1.5 * (cell + gap) + 0.02), 0.7, "muted"))
        for face, (col, row) in layout.items():
            kind = FACE_CONTENT[face]
            holder = self.own(Entity(parent=camera.ui,
                                     position=(origin_x + col * (cell + gap),
                                               origin_y + row * (cell + gap))))
            button = UIButton("", lambda f=face: self.go_to(f), parent=holder, radius=0.15,
                              scale=(cell, cell))
            label(FACE_TEXT[kind][0] or "П", (0, 0), 0.65, "strong", origin=(0, 0),
                  parent=holder)
            self.net_cells[face] = button

    def _refresh(self):
        """Обновить всё, что зависит от лицевой грани."""
        front = self.nav.front_face
        kind = self.nav.front_content
        for face, border in self.borders.items():
            accent = face_color(FACE_CONTENT[face])
            border.color = color.hex(accent) if face == front else with_alpha(accent, 0.3)
        glow = color.hex(face_color(kind))
        self.glow.color = color.rgba(glow.r, glow.g, glow.b, 0.07)

        for face, button in self.net_cells.items():
            face_kind = FACE_CONTENT[face]
            if face == front:
                fill = face_color(face_kind)
            else:
                fill = settings.BUTTON_COLOR if face_kind == "hub" else mode_dim(face_kind)
            button.color = color.hex(fill)
            button.highlight_color = color.hex(fill).tint(0.15)
            button.model.setColorScale(button.color)

        if kind == "hub":
            self.hint.text = "статистика, настройки и игроки - кнопки прямо на грани"
        elif kind == "custom":
            self.hint.text = "Enter или клик по грани - собрать свою тренировку"
        else:
            self.hint.text = "Enter или клик по грани - начать  •  стрелки - повернуть куб"
        self.level_switch.enabled = kind not in ("hub", "custom")

    # ---------- управление ----------
    def turn(self, direction):
        if self.entering or self.dialog is not None:
            return False
        if not self.nav.move(direction):
            return False
        if direction == "right":
            self.cube.yaw_turns += 1
        elif direction == "left":
            self.cube.yaw_turns -= 1
        self.cube.set_state(self.cube.yaw_turns, self.nav.pitch)
        MainMenu.remembered_nav = (self.nav.yaw, self.nav.pitch)
        MainMenu.remembered_turns = self.cube.yaw_turns
        self._refresh()
        return True

    def go_to(self, face):
        """Повернуть куб к грани face кратчайшим путём."""
        for step in self.nav.path_to(face):
            self.turn(step)

    def open_front(self):
        """Открыть режим на лицевой грани: камера «влетает» в грань."""
        kind = self.nav.front_content
        if self.entering or self.dialog is not None or kind == "hub":
            return
        self.entering = True
        rig = camera.parent                  # EditorCamera из engine/camera.py
        if prefs.reduce_motion or not hasattr(rig, "target_z"):
            self.start(kind)
            return
        rig.target_z = -SIZE * 0.6
        invoke(self.start, kind, delay=FLY_SECONDS)

    def input(self, key):
        if self.dialog is not None or self.entering:
            return
        if key in KEYS:
            self.turn(KEYS[key])
        elif key in ("enter", "space"):
            self.open_front()
        elif key == "left mouse down":
            self.drag_start = mouse_position()
        elif key == "left mouse up" and self.drag_start is not None:
            delta = mouse_position() - self.drag_start
            self.drag_start = None
            if max(abs(delta.x), abs(delta.y)) > 0.06:
                # Потянули мышью - куб поворачивается вслед за рукой
                if abs(delta.x) > abs(delta.y):
                    self.turn("left" if delta.x > 0 else "right")
                else:
                    self.turn("up" if delta.y < 0 else "down")
                return
            self._click(mouse.hovered_entity)

    def _click(self, entity):
        face = self.cube.face_of(entity)
        if face is None:
            return
        if face == self.nav.front_face:
            if not isinstance(entity, Button):   # кнопки на грани срабатывают сами
                self.open_front()
        else:
            self.go_to(face)                     # клик по краю соседней грани - повернуть

    def set_level(self, level):
        self.level = level
        MainMenu.remembered_level = level

    def start(self, mode):
        if self.dialog is not None:
            return
        # «Моя тренировка» - сначала экран-конструктор, остальные режимы сразу
        if mode == "custom":
            self.navigate("custom")
        else:
            self.navigate(mode, level=self.level)

    # ---------- тренировка по коду ----------
    def open_code_dialog(self):
        if self.dialog is None and not self.entering:
            self.dialog = CodeDialog(self.start_by_code, self.close_code_dialog)

    def close_code_dialog(self):
        if self.dialog is not None:
            dispose(self.dialog)
            self.dialog = None

    def start_by_code(self, mode, level, seed):
        self.close_code_dialog()
        self.navigate(mode, level=level, seed=seed, locked=True)

    def close(self):
        self.close_code_dialog()
        super().close()
