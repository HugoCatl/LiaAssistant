"""
Crea la presencia de Lia. Por defecto el orbe minimalista profesional.
Modos opcionales (opt-in vía variable de entorno):
  - LIVE2D_MODEL_PATH=<.model3.json|.model.json>  -> personaje Live2D
  - LIA_MASCOT=cat                                 -> gato dibujado (legacy)
"""
import os

from config import settings
from src.gui.orb_mascot import OrbMascot


def _live2d_model_path() -> str:
    """Devuelve la ruta al modelo Live2D solo si está configurada y existe."""
    configured = (settings.live2d_model_path or "").strip()
    if configured and os.path.isfile(configured) and configured.endswith(
        (".model3.json", ".model.json")
    ):
        return configured
    return ""


def make_mascot():
    """Devuelve la presencia adecuada: orbe por defecto; Live2D/gato si se pide."""
    model_path = _live2d_model_path()
    if model_path:
        try:
            from src.gui.live2d_mascot import Live2DMascot, configure_surface_format
            configure_surface_format()
            print(f"[mascot] Modo personaje Live2D: {model_path}")
            return Live2DMascot(model_path, scale=settings.live2d_scale)
        except Exception as e:
            print(f"[mascot] No se pudo cargar Live2D ({e}); usando el orbe.")

    if os.environ.get("LIA_MASCOT", "").lower() == "cat":
        from src.gui.mascot import MascotWidget
        print("[mascot] Modo gato (legacy).")
        return MascotWidget()

    print("[mascot] Usando el orbe minimalista (por defecto).")
    return OrbMascot()
