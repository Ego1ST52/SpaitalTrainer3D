"""Звуки: короткие сигналы, которые программа генерирует сама (без чужих файлов).

Каждый звук - несколько нот-синусоид с мягким затуханием. При первом
запуске они записываются как WAV в служебную папку программы, дальше
просто проигрываются. Громкость - из настроек игрока ("sound").
"""

import math
import os
import struct
import tempfile
import wave
from pathlib import Path

from core.preferences import prefs

RATE = 22050
VERSION = 1            # поменять, если изменились ноты - файлы перезапишутся

# Звук: [(частота Гц, длительность с), ...]
SOUNDS = {
    "correct": [(660, 0.08), (880, 0.14)],
    "wrong": [(233, 0.12), (175, 0.2)],
    "turn": [(1400, 0.025)],
    "level_up": [(523, 0.07), (659, 0.07), (784, 0.07), (1047, 0.16)],
    "achievement": [(784, 0.09), (988, 0.09), (1175, 0.09), (1568, 0.3)],
}
VOLUME = {"off": 0.0, "quiet": 0.3, "loud": 0.75}


def render(notes, rate=RATE):
    """Ноты -> байты 16-битного моно-звука. У каждой ноты быстрое нарастание
    и плавное затухание - так нет щелчков на стыках."""
    frames = bytearray()
    for frequency, duration in notes:
        count = int(rate * duration)
        attack = max(1, int(rate * 0.005))
        for i in range(count):
            envelope = min(1.0, i / attack) * math.exp(-4.0 * i / count)
            sample = math.sin(2 * math.pi * frequency * i / rate) * envelope
            frames += struct.pack("<h", int(sample * 0.8 * 32767))
    return bytes(frames)


def sound_folder():
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(base) / "SpatialTrainer3D" / "sounds"


def prepare(folder=None):
    """Записать WAV-файлы (если их ещё нет). Возвращает {имя: путь}."""
    folder = Path(folder) if folder else sound_folder()
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, notes in SOUNDS.items():
        path = folder / f"{name}_v{VERSION}.wav"
        if not path.exists():
            with wave.open(str(path), "wb") as file:
                file.setnchannels(1)
                file.setsampwidth(2)
                file.setframerate(RATE)
                file.writeframes(render(notes))
        paths[name] = path
    return paths


_paths = None


def play(name):
    """Проиграть звук с громкостью из настроек. Ошибки звука (нет колонок,
    нет звуковой карты) игру не ломают - просто тишина."""
    global _paths
    volume = VOLUME[prefs.get("sound")]
    if volume == 0:
        return None
    try:
        if _paths is None:
            _paths = prepare()
        from ursina import Audio
        return Audio(_paths[name], volume=volume, auto_destroy=True)
    except Exception as error:          # звук - не главное, без него можно играть
        print("Звук недоступен:", error)
        return None
