"""
Logging a fichero (rotativo) + traduccion de errores a lenguaje humano.

El log vive en %LOCALAPPDATA%/LiaAssistant/lia.log para poder diagnosticar
problemas despues de instalar, sin tocar la terminal.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler

from config.paths import app_data_dir


def setup_logging() -> str:
    log_path = app_data_dir() / "lia.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        fh = RotatingFileHandler(log_path, maxBytes=512 * 1024, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)

    def _hook(exctype, value, tb):
        logging.getLogger("lia").critical("Excepcion no capturada", exc_info=(exctype, value, tb))
    sys.excepthook = _hook

    logging.getLogger("lia").info("Logging iniciado en %s", log_path)
    return str(log_path)


def friendly_error(msg: str) -> str:
    """Convierte un mensaje de error tecnico en algo entendible para el usuario."""
    m = (msg or "").lower()
    if ("api key" in m or "api_key" in m or "permission_denied" in m
            or "401" in m or "403" in m or ("invalid" in m and "key" in m)):
        return "Tu clave de Gemini no es válida o ha caducado. Revísala en Ajustes (⚙)."
    if "quota" in m or "429" in m or "resource_exhausted" in m or "rate" in m:
        return "Has alcanzado el límite de uso de la API de Gemini. Prueba de nuevo en un rato."
    if ("network" in m or "connection" in m or "timed out" in m or "timeout" in m
            or "getaddrinfo" in m or "failed to establish" in m or "ssl" in m
            or "name resolution" in m or "unreachable" in m):
        return "Parece que no hay conexión a internet. Comprueba tu red e inténtalo otra vez."
    return "Ha ocurrido un problema. Si se repite, échale un ojo al registro (lia.log)."
