# 📈 LIA — Estado del proyecto

> Documento vivo. Para el "qué hace" ver [README.md](README.md); para el "cómo está hecho" ver [ARQUITECTURA.md](ARQUITECTURA.md).

## Resumen

LIA está **funcionalmente completa** y se distribuye como **un único `.exe` autoinstalable**. ~100 pruebas en verde. A partir de aquí, las siguientes fases van de "que nunca se rompa" → "que razone bien" → "que sea más potente".

---

## ✅ Fases 1-5 — Hecho

**Presencia e interfaz**
- Orbe minimalista state-reactive en el escritorio (clic / doble-clic / arrastre).
- Panel glassmorphic con **burbujas de chat reales**: streaming, "escribiendo…", timestamps, Markdown.
- Bandeja del sistema (mostrar/ocultar/salir), pantalla de carga, **chime** de recordatorios.
- Menú de info rediseñado; atajos `Esc` (cerrar) y `↑` (último mensaje).

**Inteligencia**
- Memoria conversacional entre turnos + historial persistente.
- Búsqueda semántica local (fastembed/ONNX).
- Auto-enlazado de notas afines, auto-tags de entidades, clustering de temas, resumen diario.
- Edición fina de notas (`editar_nota`).
- Recordatorios proactivos con ML que aprende del feedback (anti-spam afinado).
- Caching implícito de Gemini aprovechado (system prompt estable por hora).
- Reglas de grafo (entidad = nota propia, enlaces cruzados, propagación de relaciones).

**Captura y voz**
- Voz (Whisper local), visión de pantalla, TTS (Edge), automatización del SO.
- Enrutamiento Flash/Pro.

**Producto**
- Onboarding plug-and-play (nombre, clave, carpeta que se crea sola).
- `.exe` autoinstalable (PyInstaller) que se copia, crea accesos directos y se registra.
- Config y estado aislados en `%LOCALAPPDATA%/LiaAssistant`.

---

## 🔴 Fase 6 — Que nunca se quede colgada ni pierda datos — ✅ HECHO

| # | Problema | Fix aplicado |
|---|---|---|
| 1 | ✅ Sin timeout en llamadas a Gemini | Timeout 120s + 1 reintento (408/429/5xx) en ambos workers; **Esc cancela** el turno en curso |
| 2 | ✅ Escritura de notas no atómica | `_atomic_write` (temporal + `os.replace`) en create/write/append/editar |
| 3 | ✅ Sin instancia única | `QLockFile` en `main.py`; segunda instancia avisa y sale |

---

## 🟠 Fase 7 — Que el cerebro no mienta ni se parta a medias

Esto es "si no relaciona bien, no es útil" — el corazón de la promesa del producto.

| # | Problema | Estado |
|---|---|---|
| 4 | ✅ Búsqueda semántica sin umbral | `min_score=0.30` en ambas rutas; si nada lo supera, "no encontré nada" |
| 5 | ✅ Sin deduplicación de entidades (Guille/Guillermo) | `create_note` detecta títulos casi iguales (difflib, sin acentos) y pide reutilizar; escape `permitir_similar=True` |
| 6 | ✅ Grafo sin verificación posterior | **Jardinero del vault** (`vault_gardener.py`): herramienta `revisar_memoria` — repara backlinks unidireccionales solo, reporta rotos/duplicados/huérfanas para que Lia pregunte antes de fusionar. Con **memoria de decisiones** (`graph_decisions.json`): si respondes "son distintas" o "déjala suelta", no vuelve a preguntarlo (`marcar_entidades_distintas`, `ignorar_nota_suelta`). Acceso directo en el panel ⓘ |
| 7 | ✅ Auto-enlazado de un solo sentido | `add_backlink`: el enlace de vuelta se escribe DE VERDAD en la nota destino (idempotente) |

---

## 🟡 Fase 8 — Primera impresión y confianza

| # | Problema | Estado |
|---|---|---|
| 8 | ✅ Onboarding no validaba la clave | Al guardar: `count_tokens` real (gratis, timeout 10s); clave inválida no pasa; sin internet no bloquea |
| 9 | ✅ Carpeta no validada | Test de escritura real (archivo sonda) al guardar |
| 10 | ✅ Warmup ciego del scorer | `MIN_TRAIN` 10 → 6 (aprende antes, la L2 evita sobreajuste) |

---

## 🟢 Fase 9 — Pulido / observabilidad

| # | Problema | Estado |
|---|---|---|
| 11 | 🔶 `except Exception:` silenciosos | Logueados los de I/O crítico (auto-link, backlinks, notas); resto pendiente de barrido |
| 12 | ✅ Sin reintentos de red | `HttpRetryOptions(attempts=2)` con backoff (cayó con la Fase 6.1) |
| 13 | ✅ Fallos silenciosos de auto-link | Aviso en `lia.log` una sola vez si el índice no carga |

---

## 🚀 Fase 10 — Potenciar (subir el techo, no arreglar nada roto)

### Construyen sobre lo que ya existe (esfuerzo bajo-medio)
| # | Idea | Por qué |
|---|---|---|
| 14 | ✅ **Ficha de entidad** ("cuéntame sobre Guille") | Hecho: `entity_card.py` → herramienta `ficha_entidad` (nota propia + menciones dispersas + afines semánticas; resolución difusa Guille→Guillermo) |
| 15 | **Resurgir conexiones olvidadas** — detectar en la propia conversación (no solo al crear nota) que algo se parece a algo de hace semanas | `ProactiveEngine` + `semantic_index` ya existen; falta el disparador durante la charla |
| 16 | **Recordatorios que nacen de las notas** — "revisar esto la semana que viene" escrito en una nota → sugerencia de recordatorio | `reminders.py` ya existe; falta el puente desde contenido pasivo |
| 17 | **Resumen semanal/mensual**, no solo diario — tendencias en el tiempo | Extensión directa de `daily_summary.py` + `topic_clusters.py` |

### Palancas de calidad de respuesta (esfuerzo medio)
| # | Idea | Por qué |
|---|---|---|
| 18 | ✅ **Ranking por recencia** | Hecho: boost por frescura (vida media 30 días) como desempate; el umbral de relevancia se aplica ANTES sobre el coseno crudo |
| 19 | ✅ **Detección de contradicciones** | Hecho: regla 4 del grafo — leer antes de guardar, avisar del conflicto y SUSTITUIR (no acumular versiones) en todas las notas |

### Palancas grandes (esfuerzo alto, cambian de categoría el producto)
| # | Idea | Por qué |
|---|---|---|
| 20 | ✅ **Vista de grafo dentro de la app** | Hecho: `src/gui/graph_view.py` — layout de fuerzas en numpy + canvas QPainter; entrada "🕸️ Ver mi grafo" en el panel ⓘ |
| 21 | **Modo 100% offline con LLM local** (p. ej. Ollama) como alternativa a Gemini | El mayor salto de privacidad; refuerza el mensaje "local-first" |
| 22 | ✅ **Separación de contextos** trabajo/personal | Hecho: tag `contexto/trabajo|personal` en las notas + filtro `contexto=` en `search_notes_semantic` (las notas sin esfera siempre entran) |

---

## 🗺️ Orden de ejecución recomendado

1. **Fase 6** — sin esto nada más importa (robustez ante fallos/corrupción).
2. **Fase 7**, empezando por **#4 y #5** (rápidos) y dejando **#6 (jardinero del vault)** como pieza de diseño aparte.
3. **Fase 8** — onboarding a prueba de fallos.
4. **Fase 9** cuando haya hueco.
5. **Fase 10**: **#14 y #15** primero (mejor ratio impacto/esfuerzo, reutilizan piezas existentes); **#21 (LLM local)** es el que más cambiaría la percepción del producto pero se deja para cuando el resto esté sólido.

---

## 🔧 Notas de mantenimiento

**Reconstruir el `.exe`** (tras tocar código):
```bash
.\venv\Scripts\pyinstaller --noconfirm --clean packaging/lia.spec
# resultado en dist/LIA.exe (~178 MB)
```
> El `.exe` no se actualiza solo: hay que recompilar para que los cambios lleguen al archivo.

**Resetear a "usuario nuevo"** (para grabar una demo): borrar `%LOCALAPPDATA%/LiaAssistant` (config, historial, feedback, logs).

**Fricciones irreducibles al repartir** (no son código): el aviso de SmartScreen (app sin firmar) y que cada usuario ponga su propia clave gratis de Gemini.
