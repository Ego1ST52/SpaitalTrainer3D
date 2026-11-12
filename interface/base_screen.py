from ursina import *
from ursina.shaders import unlit_shader

from core import settings
from core.preferences import prefs
from engine.objects import dispose

FADE_SECONDS = 0.35


class BaseScreen(Entity):
    """Предок всех экранов. Всё, что экран создаёт через own(),
    удаляется при закрытии экрана."""

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self._owned = []
        # Экран плавно проявляется: поверх всего лежит тёмная пелена,
        # которая за FADE_SECONDS становится прозрачной.
        # При настройке «меньше движения» экран появляется сразу.
        if not prefs.reduce_motion:
            veil = self.own(Entity(parent=camera.ui, model="quad", scale=(4, 2), z=-0.9,
                                   color=color.hex(settings.BACKGROUND),
                                   shader=unlit_shader))
            veil.fade_out(duration=FADE_SECONDS)

    def own(self, obj):
        self._owned.append(obj)
        return obj

    def spoken_text(self):
        """Что прочитать вслух при озвучке: вопрос и пояснение под ним."""
        parts = [getattr(self, name).text for name in ("question", "subtitle")
                 if getattr(self, name, None) is not None]
        return ". ".join(" ".join(p.split()) for p in parts if p)

    def navigate(self, name, **kwargs):
        # Небольшая задержка: нельзя удалять кнопку прямо во время её клика
        invoke(self.manager.go, name, delay=0.05, **kwargs)

    def close(self):
        for obj in self._owned:
            dispose(obj)
        self._owned = []
        dispose(self)
