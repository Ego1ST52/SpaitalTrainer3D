from ursina import *

from core import settings
from interface.base_screen import BaseScreen
from interface.ui_kit import Avatar, FRONT, label, Panel, UIButton

COLUMNS = 4
CARD_W, CARD_H = 0.38, 0.12
MAX_CARDS = 8


def sessions_text(count):
    """1 тренировка, 3 тренировки, 7 тренировок."""
    if count % 10 == 1 and count % 100 != 11:
        word = "тренировка"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = "тренировки"
    else:
        word = "тренировок"
    return f"{count} {word}"


class ProfilesScreen(BaseScreen):
    """Выбор игрока и создание нового. У каждого игрока своя статистика
    и свои настройки.
    users - список из Database.list_users() или None (база недоступна);
    on_select(id) - выбрать игрока; on_create(имя) -> текст ошибки или None."""

    def __init__(self, manager, users, current_id, on_select, on_create):
        super().__init__(manager)
        self.on_select = on_select
        self.on_create = on_create
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05

        self.own(label("Игроки", (left, 0.42), 2.0, "strong"))
        self.own(label("У каждого - своя статистика, прогресс и настройки",
                       (left, 0.365), 0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06),
                          variant="ghost"))

        if users is None:
            self.own(label("Не удалось прочитать данные из базы.", (0, 0.1), 1.0,
                           "wrong", origin=(0, 0)))
            return

        for i, user in enumerate(users[:MAX_CARDS]):
            row, col = divmod(i, COLUMNS)
            x = (col - (COLUMNS - 1) / 2) * (CARD_W + 0.03)
            y = 0.22 - row * (CARD_H + 0.03)
            self._card(user, (x, y), user["id"] == current_id)
        if len(users) > MAX_CARDS:
            self.own(label(f"и ещё {len(users) - MAX_CARDS}", (0, -0.07), 0.8,
                           "muted", origin=(0, 0)))

        # Новый игрок
        self.own(Panel(0.9, 0.2, position=(0, -0.26)))
        self.own(label("Новый игрок", (-0.41, -0.195), 0.9, "accent"))
        self.own(label("введите имя (до 20 букв) и нажмите «Создать» или Enter",
                       (-0.25, -0.195), 0.75, "muted"))
        self.name_field = self.own(InputField(position=(-0.12, -0.26, FRONT * 2),
                                              scale=(0.5, 0.06), character_limit=20,
                                              color=color.hex(settings.BUTTON_COLOR),
                                              active=True))    # печатать можно сразу
        self.name_field.submit_on = ["enter"]
        self.name_field.on_submit = self.create
        self.own(UIButton("Создать", self.create, position=(0.29, -0.26),
                          scale=(0.2, 0.06), variant="primary"))
        self.error = self.own(label("", (-0.41, -0.325), 0.8, "wrong"))

    def _card(self, user, position, current):
        card = self.own(Entity(parent=camera.ui, position=position))
        button = UIButton("", lambda uid=user["id"]: self.select(uid), parent=card,
                          scale=(CARD_W, CARD_H), radius=0.2,
                          variant="primary" if current else "secondary")
        left = -CARD_W / 2 + 0.05
        Avatar(user["name"], user["color"], (left, 0, FRONT), size=0.06, parent=card)
        label(user["name"], (left + 0.05, 0.018), 1.05, "strong", parent=card)
        caption = "сейчас играет" if current else sessions_text(user["sessions"])
        label(caption, (left + 0.05, -0.02), 0.75, "text" if current else "muted",
              parent=card)
        return button

    def select(self, user_id):
        self.on_select(user_id)
        self.navigate("menu")

    def create(self):
        error = self.on_create(self.name_field.text)
        if error:
            self.error.text = error
        else:
            self.navigate("menu")
