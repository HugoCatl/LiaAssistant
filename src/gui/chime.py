"""
Chime de notificación para los recordatorios.

Sintetiza un sonido breve y agradable (dos notas con desvanecido) en un WAV PCM,
sin assets externos ni licencias — coherente con el resto del proyecto (orbe
dibujado, sin recursos). El fichero se cachea en el directorio de datos de la app.
"""
import math
import struct
import wave

from config.paths import runtime_file

_CHIME_PATH = None
_SAMPLE_RATE = 44100


def _write_chime(path: str):
    """Genera un chime de dos notas (La5 -> Mi6) suave con fundido de entrada/salida."""
    notes = [(880.0, 0.16), (1318.5, 0.30)]  # (frecuencia Hz, duración s)
    frames = bytearray()
    for freq, dur in notes:
        n = int(_SAMPLE_RATE * dur)
        for i in range(n):
            t = i / _SAMPLE_RATE
            # Envolvente: ataque rápido y caída exponencial (campana suave)
            env = min(1.0, i / (_SAMPLE_RATE * 0.012)) * math.exp(-3.2 * (i / n))
            # Tono + un armónico tenue para darle cuerpo
            sample = 0.6 * math.sin(2 * math.pi * freq * t) + 0.15 * math.sin(2 * math.pi * 2 * freq * t)
            value = int(max(-1.0, min(1.0, sample * env)) * 32767 * 0.5)
            frames += struct.pack("<h", value)

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(bytes(frames))


def chime_path() -> str:
    """Devuelve la ruta del WAV del chime, generándolo la primera vez."""
    global _CHIME_PATH
    if _CHIME_PATH is None:
        path = runtime_file("lia_chime.wav")
        try:
            import os
            if not os.path.exists(path):
                _write_chime(path)
        except Exception:
            pass
        _CHIME_PATH = path
    return _CHIME_PATH
