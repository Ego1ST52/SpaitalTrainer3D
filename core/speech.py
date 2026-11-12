"""Озвучка заданий: читает условие вслух голосом Windows, без интернета.

Используется встроенный в Windows синтезатор речи (System.Speech). Его
запускаем отдельным процессом PowerShell, чтобы игра не подвисала, пока
звучит фраза. Текст передаём через стандартный ввод, а не в командной
строке, - так никакой текст не может «сломать» команду.
Новая фраза прерывает предыдущую. Если голоса нет (не Windows) - тишина.
"""

import subprocess
import sys

from core.preferences import prefs

# Скрипт PowerShell: прочитать текст из ввода и произнести его русским
# голосом, если он установлен (иначе - голосом по умолчанию)
SCRIPT = (
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$ru = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like 'ru*' }"
    " | Select-Object -First 1; "
    "if ($ru) { $s.SelectVoice($ru.VoiceInfo.Name) }; "
    "$s.Rate = 1; "
    "$s.Speak([Console]::In.ReadToEnd())"
)

_process = None


def available():
    return sys.platform == "win32"


def stop():
    """Прервать фразу, которая звучит сейчас."""
    global _process
    if _process is not None and _process.poll() is None:
        _process.terminate()
    _process = None


def speak(text, force=False):
    """Произнести text, если озвучка включена в настройках (или force=True).
    Возвращает True, если фраза отправлена синтезатору."""
    global _process
    if not text or not (force or prefs.get("speech")) or not available():
        return False
    stop()
    try:
        _process = subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        _process.stdin.write(text.encode("utf-8"))
        _process.stdin.close()
    except OSError:
        _process = None
        return False
    return True
