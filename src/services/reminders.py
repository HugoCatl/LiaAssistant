"""
Recordatorios con hora. Almacenamiento simple en JSON (app-data) compartido
entre las herramientas que usa Gemini y el servicio que los dispara.
"""
import json
from datetime import datetime, timedelta

from config.paths import app_data_dir

_FILE = app_data_dir() / "reminders.json"
_FMT = "%Y-%m-%d %H:%M"


def _load() -> list:
    if _FILE.exists():
        try:
            return json.loads(_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(items: list):
    _FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_when(fecha_hora: str, en_minutos: int) -> datetime:
    if en_minutos and int(en_minutos) > 0:
        return datetime.now() + timedelta(minutes=int(en_minutos))
    s = (fecha_hora or "").strip().replace("T", " ")
    for fmt in (_FMT, "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == "%H:%M":  # solo hora -> hoy (o manana si ya paso)
                now = datetime.now()
                dt = now.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
                if dt <= now:
                    dt += timedelta(days=1)
            return dt
        except ValueError:
            continue
    raise ValueError("formato de fecha/hora no reconocido")


def crear_recordatorio(texto: str, fecha_hora: str = "", en_minutos: int = 0) -> str:
    """
    Crea un recordatorio que avisara al usuario a una hora concreta mediante una
    notificacion junto a la mascota.

    Args:
        texto: que hay que recordar.
        fecha_hora: hora exacta en formato 'YYYY-MM-DD HH:MM' (24h). Usa la fecha
            y hora actuales que se te indican para calcular expresiones como
            'manana a las 9' o 'hoy a las 17:30'.
        en_minutos: alternativa rapida; dentro de N minutos a partir de ahora.

    Returns:
        Confirmacion con la hora programada.
    """
    try:
        when = _parse_when(fecha_hora, en_minutos)
    except ValueError:
        return "No entendí la hora del recordatorio. Dímelo como 'hoy a las 17:30' o 'en 20 minutos'."
    due = when.strftime(_FMT)
    items = _load()
    # Evitar duplicados: mismo texto y misma hora aun pendiente
    for i in items:
        if not i.get("done") and i.get("texto") == texto and i.get("due") == due:
            return f"Ya tenías ese recordatorio para el {when.strftime('%d/%m a las %H:%M')}."
    items.append({
        "id": int(datetime.now().timestamp() * 1000),
        "texto": texto,
        "due": due,
        "done": False,
    })
    _save(items)
    return f"Recordatorio guardado para el {when.strftime('%d/%m a las %H:%M')}: {texto}"


def listar_recordatorios() -> str:
    """Lista los recordatorios pendientes del usuario con su hora."""
    pend = [i for i in _load() if not i.get("done")]
    if not pend:
        return "No tienes recordatorios pendientes."
    pend.sort(key=lambda i: i.get("due", ""))
    lineas = [f"- {i['texto']} ({i['due']})" for i in pend]
    return "Recordatorios pendientes:\n" + "\n".join(lineas)


def pop_due(now: datetime = None) -> list:
    """Devuelve los textos de los recordatorios vencidos y los marca como hechos."""
    now = now or datetime.now()
    items = _load()
    due_texts = []
    changed = False
    for i in items:
        if i.get("done"):
            continue
        try:
            due = datetime.strptime(i["due"], _FMT)
        except Exception:
            continue
        if due <= now:
            due_texts.append(i["texto"])
            i["done"] = True
            changed = True
    if changed:
        _save(items)
    return due_texts
