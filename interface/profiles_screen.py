from ursina import *

from core import settings
from engine.objects import dispose
from interface.base_screen import BaseScreen
from interface.confirm_dialog import ConfirmDialog
from interface.ui_kit import Avatar, FRONT, label, Panel, UIButton

COLUMNS = 4
CARD_W, CARD_H = 0.38, 0.12
MAX_CARDS = 8
CREATE_HINT = "введите имя (до 20 букв) и нажмите «Создать» или Enter"


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
    on_select(id) - выбрать игрока; on_create(имя) -> текст ошибки или None;
    on_rename(id, имя) и on_delete(id) -> текст ошибки или None."""

    def __init__(self, manager, users, current_id, on_select, on_create,
                 on_rename=None, on_delete=None, on_report=None):
        super().__init__(manager)
        self.on_select = on_select
        self.on_create = on_create
        self.on_rename = on_rename
        self.on_delete = on_delete
        self.renaming_id = None     # кого переименовываем (None - создаём нового)
        self.dialog = None
        left = window.top_left.x + 0.05
        right = window.top_right.x - 0.05

        self.own(label("Игроки", (left, 0.42), 2.0, "strong"))
        self.own(label("У каждого - своя статистика, прогресс и настройки",
                       (left, 0.365), 0.85, "muted"))
        self.own(UIButton("В меню", lambda: self.navigate("menu"),
                          position=(right - 0.09, 0.42), scale=(0.18, 0.06),
                          variant="ghost"))
        # Отчёт для учителя: таблица по всем игрокам (CSV для Excel)
        self.on_report = on_report
        self.report_note = self.own(label("", (right, 0.365), 0.75, "muted", origin=(0.5, 0)))
        if on_report is not None:
            self.own(UIButton("Отчёт для учителя", self.make_report,
                              position=(right - 0.33, 0.42), scale=(0.26, 0.06)))
            # Задание для класса: код с ограничением по времени и общая таблица
            self.own(UIButton("Задание для класса", lambda: self.navigate("class_task"),
                              position=(right - 0.62, 0.42), scale=(0.28, 0.06)))

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
        self.panel_title = self.own(label("Новый игрок", (-0.41, -0.195), 0.9, "accent"))
        self.panel_hint = self.own(label(CREATE_HINT, (-0.25, -0.195), 0.75, "muted"))
        self.name_field = self.own(InputField(position=(-0.12, -0.26, FRONT * 2),
                                              scale=(0.5, 0.06), character_limit=20,
                                              color=color.hex(settings.BUTTON_COLOR),
                                              active=True))    # печатать можно сразу
        self.name_field.submit_on = ["enter"]
        self.name_field.on_submit = self.submit
        self.submit_button = self.own(UIButton("Создать", self.submit, position=(0.29, -0.26),
                                               scale=(0.2, 0.06), variant="primary"))
        self.cancel_button = self.own(UIButton("Отмена", self.cancel_rename,
                                               position=(0.29, -0.325), scale=(0.2, 0.045),
                                               variant="ghost", text_size=0.8))
        self.cancel_button.enabled = False
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
        # Маленькие кнопки в углу: «изм» - переименовать, «×» - удалить
        corner_y = CARD_H / 2 - 0.025
        UIButton("изм", lambda u=user: self.start_rename(u), parent=card, variant="ghost",
                 position=(CARD_W / 2 - 0.08, corner_y, FRONT * 2), scale=(0.06, 0.032),
                 text_size=0.65)
        UIButton("×", lambda u=user: self.ask_delete(u), parent=card, variant="ghost",
                 position=(CARD_W / 2 - 0.026, corner_y, FRONT * 2), scale=(0.035, 0.032),
                 text_size=0.9)
        return button

    def select(self, user_id):
        self.on_select(user_id)
        self.navigate("menu")

    def submit(self):
        """Кнопка под полем: «Создать» или «Сохранить» (при переименовании)."""
        if self.renaming_id is not None:
            self.rename()
        else:
            self.create()

    def create(self):
        error = self.on_create(self.name_field.text)
        if error:
            self.error.text = error
        else:
            self.navigate("menu")

    # ---------- переименование ----------
    def start_rename(self, user):
        if self.dialog is not None:
            return
        self.renaming_id = user["id"]
        self.panel_title.text = f"Новое имя для «{user['name']}»"
        self.panel_hint.text = ""
        self.name_field.text = user["name"]
        self.submit_button.text = "Сохранить"
        self.cancel_button.enabled = True
        self.error.text = ""

    def cancel_rename(self):
        self.renaming_id = None
        self.panel_title.text = "Новый игрок"
        self.panel_hint.text = CREATE_HINT
        self.name_field.text = ""
        self.submit_button.text = "Создать"
        self.cancel_button.enabled = False
        self.error.text = ""

    def rename(self):
        if self.on_rename is None:
            return
        error = self.on_rename(self.renaming_id, self.name_field.text)
        if error:
            self.error.text = error
        else:
            self.navigate("profiles")       # открыть экран заново с новым именем

    # ---------- удаление ----------
    def ask_delete(self, user):
        if self.dialog is not None:
            return
        self.dialog = ConfirmDialog(
            f"Удалить игрока «{user['name']}»?",
            f"Удалятся все его тренировки ({sessions_text(user['sessions'])}), достижения "
            "и настройки. Это нельзя отменить.",
            "Удалить", lambda: self.delete(user["id"]), self.close_dialog)

    def close_dialog(self):
        if self.dialog is not None:
            dispose(self.dialog)
            self.dialog = None

    def delete(self, user_id):
        self.close_dialog()
        if self.on_delete is None:
            return
        error = self.on_delete(user_id)
        if error:
            self.error.text = error
        else:
            self.navigate("profiles")       # открыть экран заново без удалённого

    def make_report(self):
        self.report_note.text = self.on_report()

    def close(self):
        self.close_dialog()
        super().close()
