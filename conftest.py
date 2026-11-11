"""Общие заготовки (фикстуры) для тестов pytest."""

import pytest


@pytest.fixture(scope="session")
def ursina_app():
    """Одно приложение Ursina без окна на все тесты интерфейса.
    Ursina можно создать только один раз за запуск, поэтому оно общее."""
    ursina = pytest.importorskip("ursina")
    try:
        app = ursina.Ursina(window_type="offscreen", size=(640, 360))
    except Exception as error:   # нет видеокарты/драйвера - тесты пропускаем
        pytest.skip(f"Ursina не запускается без окна: {error}")
    return app
