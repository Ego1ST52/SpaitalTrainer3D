"""Куб-навигатор главного меню: какая грань сейчас перед игроком.
Без Ursina - проверяется автотестами.

Куб устроен как глобус:
  * «пояс» из четырёх граней крутится стрелками ← и →;
  * стрелка ↑ наклоняет куб и показывает верхнюю грань, ↓ - нижнюю;
  * из верхней/нижней грани можно только вернуться обратно на пояс.
Так текст на гранях всегда читается, а игрок не теряется.

Грани называются по их месту на кубе: front, right, back, left, top, bottom.
"""

RING = ["front", "right", "back", "left"]     # пояс по часовой, если смотреть сверху

# Что на какой грани
FACE_CONTENT = {
    "front": "rotation",
    "right": "matching",
    "back": "projection",
    "left": "construction",
    "top": "workshop",         # «Мастерская»: своя тренировка и новые режимы
    "bottom": "hub",           # профиль: статистика, настройки, игроки
}
CONTENT_FACE = {content: face for face, content in FACE_CONTENT.items()}


class CubeNavigator:
    def __init__(self, yaw=0, pitch=0):
        self.yaw = yaw % 4      # какая грань пояса спереди (индекс в RING)
        self.pitch = pitch      # 0 - пояс, 1 - видна верхняя грань, -1 - нижняя

    @property
    def front_face(self):
        if self.pitch == 1:
            return "top"
        if self.pitch == -1:
            return "bottom"
        return RING[self.yaw]

    @property
    def front_content(self):
        return FACE_CONTENT[self.front_face]

    def move(self, direction):
        """direction: 'left', 'right', 'up', 'down'. Возвращает True, если куб
        повернулся. Влево/вправо на верхней или нижней грани не работают."""
        if direction in ("left", "right"):
            if self.pitch != 0:
                return False
            self.yaw = (self.yaw + (1 if direction == "right" else -1)) % 4
            return True
        if direction == "up" and self.pitch < 1:
            self.pitch += 1
            return True
        if direction == "down" and self.pitch > -1:
            self.pitch -= 1
            return True
        return False

    def path_to(self, face):
        """Список нажатий стрелок, который приведёт к грани face (кратчайший)."""
        steps = []
        if face in ("top", "bottom"):
            target_pitch = 1 if face == "top" else -1
            if self.pitch == target_pitch:
                return []
            if self.pitch != 0:                   # сначала вернуться на пояс
                steps.append("down" if self.pitch == 1 else "up")
            steps.append("up" if target_pitch == 1 else "down")
            return steps
        if self.pitch != 0:
            steps.append("down" if self.pitch == 1 else "up")
        delta = (RING.index(face) - self.yaw) % 4
        if delta == 3:
            steps.append("left")
        else:
            steps.extend(["right"] * delta)
        return steps
