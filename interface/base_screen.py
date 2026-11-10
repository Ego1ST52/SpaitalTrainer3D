from ursina import *

from engine.objects import dispose


class BaseScreen(Entity):
    """Предок всех экранов. Всё, что экран создаёт через own(),
    удаляется при закрытии экрана."""

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self._owned = []

    def own(self, obj):
        self._owned.append(obj)
        return obj

    def navigate(self, name, **kwargs):
        # Небольшая задержка: нельзя удалять кнопку прямо во время её клика
        invoke(self.manager.go, name, delay=0.05, **kwargs)

    def close(self):
        for obj in self._owned:
            dispose(obj)
        self._owned = []
        dispose(self)