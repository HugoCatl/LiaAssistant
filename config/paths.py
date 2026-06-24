"""
Rutas de datos de LIA, centralizadas.

Todo lo que LIA escribe en runtime (config .env empaquetada, audios temporales,
capturas, logs) vive bajo %LOCALAPPDATA%/LiaAssistant en vez de en el directorio
actual (que al ejecutar el .exe seria Descargas). Asi no ensucia carpetas del
usuario y la config persiste entre arranques.
"""
import os
import sys
from pathlib import Path

APP_NAME = "LiaAssistant"


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def runtime_file(name: str) -> str:
    """Ruta absoluta para un archivo temporal/runtime (audio, captura, etc.)."""
    return str(app_data_dir() / name)


def env_path() -> Path:
    """
    Ruta del .env de configuracion.
      - Empaquetado (.exe): %LOCALAPPDATA%/LiaAssistant/.env (persistente).
      - Desarrollo: la raiz del proyecto (junto a main.py).
    """
    if getattr(sys, "frozen", False):
        return app_data_dir() / ".env"
    return Path(__file__).resolve().parents[1] / ".env"
