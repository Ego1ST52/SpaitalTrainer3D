import wave

from core import sounds
from core.preferences import prefs


def test_render_has_expected_length():
    data = sounds.render([(440, 0.1), (880, 0.05)], rate=8000)
    assert len(data) == 2 * (800 + 400)            # 16 бит = 2 байта на отсчёт


def test_prepare_writes_valid_wav_files(tmp_path):
    paths = sounds.prepare(tmp_path)
    assert set(paths) == set(sounds.SOUNDS)
    for path in paths.values():
        with wave.open(str(path)) as file:
            assert file.getnchannels() == 1 and file.getframerate() == sounds.RATE
            assert file.getnframes() > 0


def test_sound_off_plays_nothing():
    prefs.load({"sound": "off"})
    try:
        assert sounds.play("correct") is None
    finally:
        prefs.load({})


def test_every_volume_option_is_known():
    from core.preferences import OPTIONS
    assert set(OPTIONS["sound"]) == set(sounds.VOLUME)
