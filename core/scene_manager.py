class SceneManager:
    """Хранит фабрики экранов и переключает текущий экран.
    Не зависит от Ursina, поэтому проверяется тестами."""

    def __init__(self):
        self._factories = {}
        self._current = None

    def register(self, name, factory):
        self._factories[name] = factory

    @property
    def current(self):
        """Экран, который сейчас открыт (или None)."""
        return self._current

    def go(self, name, **kwargs):
        if name not in self._factories:
            raise KeyError(f"Неизвестный экран: {name!r}")
        if self._current is not None:
            self._current.close()
        self._current = self._factories[name](**kwargs)