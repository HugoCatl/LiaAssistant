# LiaAssistant — Estado y Roadmap (jun 2026)

## 🎯 Últimas modificaciones (esta sesión)

### ✅ Completado
1. **Limpieza total al orbe** — Eliminado: mascota gato QPainter, Live2D, modelos Cubism, scripts de preview, dependencias PyOpenGL/live2d-py. Solo queda orbe minimalista.
2. **Clustering de temas (Fase 3C)** — KMeans en numpy puro. Descubre temas latentes en notas: `get_note_clusters()` herramienta registrada.
3. **Auto-tags de entidades (Fase 3D)** — Gemini extrae `persona/Nombre`, `proyecto/Nombre`, `lugar/Sitio`. Normalización de tags (espacios → guiones para Obsidian).
4. **Memoria conversacional** — Bug crítico arreglado: cada worker ahora recuerda turnos previos. Lia ya puede sostener conversaciones multi-turno (ej: "Crea nota con portapapeles" → "¿Título?" → "Ideas" ✅).
5. **Trim de historial** — Acota memoria a 16 turnos (control de tokens) sin dejar respuestas de herramienta huérfanas.
6. **"Nueva conversación"** en menú — Botón para resetear historial y panel.

### 📊 Tests
- **68/68 verde** — +4 tests memoria conversacional, +7 tests normalización tags, +5 tests clustering

### 🗂️ Ubicación Obsidian
Vault está en: `C:\LIAI` (configurado en `.env` → `OBSIDIAN_VAULT_PATH=C:\LIAI`)

---

## 📋 Estado de las fases

| Fase | Componente | Estado | Notas |
|---|---|---|---|
| **1** | Orbe minimalista | ✅ | Sin dependencias externas, QPainter puro |
| **2** | Recordatorios proactivos | ✅ | Monitor + motor de reglas + burbuja |
| **3A** | Búsqueda semántica | ✅ | fastembed local, cosine similarity |
| **3B** | Score que aprende | ✅ | Regresión logística + feedback |
| **3C** | Clustering temas | ✅ | KMeans esférico, descubrimiento latente |
| **3D** | Auto-tags entidades | ✅ | Gemini + normalización Obsidian-valid |
| **4** | Resumen diario | ✅ | Diario AAAA-MM-DD con conexiones |
| **4.5** | Pulido profesional | ⏳ | **VER ABAJO** |
| **5** | Producto (instalador) | ⏳ | Tras validar 4.5 en uso real |

---

## 🎨 Fase 4.5 — Pulido profesional (NO es Fase 5)

**Mejoras de bajo coste + alto impacto en UX.** Deben ir **ANTES** de empaquetar.

### Tier 1 — Quick wins (≈1–2h cada uno)

1. **Icono en bandeja del sistema** (`QSystemTrayIcon`)
   - Mostrar/ocultar ventana
   - Acceso a ajustes y **salir** de verdad
   - *Por qué:* Comportamiento esperado en toda app de escritorio. Ahora no hay forma limpia de cerrar.

2. **Onboarding de primer arranque**
   - Si falta `GEMINI_API_KEY` o `OBSIDIAN_VAULT_PATH`: diálogo amable para configurar
   - En lugar de error crudo
   - *Por qué:* Crítico si otro usuario instala la app.

3. **Errores elegantes**
   - Mensajes claros: "Sin conexión", "Clave inválida", "Vault no encontrado"
   - No excepciones crudas
   - *Coste:* Integrar try/catch mejores en los workers

4. **Log a fichero**
   - Diagnóstico rotativo en `%LOCALAPPDATA%/LiaAssistant/lia.log`
   - *Por qué:* Depuración sin tocar terminal.

5. **Arranque con Windows** (opcional)
   - Acceso directo en carpeta de inicio
   - Toggle on/off en ajustes

### Tier 2 — Media jornada, alto impacto

6. **Panel de Ajustes in-app** ⭐ (TODO #1)
   - Editar: API key, vault, nombre, voz, color de acento
   - Flags proactivos (ON/OFF)
   - **Sin tocar `.env` nunca más**
   - Botón "Probar" para validar clave/vault
   - *Coste:* Nueva ventana modal + conexión a Settings

7. **Historial persistente**
   - Reabre el panel → recupera contexto reciente (SQLite)
   - *Por qué:* Continuidad entre sesiones

8. **Render Markdown en respuestas** ⭐ (TODO #2)
   - Negritas, listas, código formateado
   - **Mayor salto visual** que el texto plano actual
   - *Coste:* QTextBrowser con CSS o `marked.js` si es HTML

9. **Captura rápida**
   - Atajo (ej. Ctrl+Shift+L) → escribes → Enter guarda nota al instante
   - Sin abrir conversación
   - *Por qué:* Flujo ultra rápido para notas cortas

### Tier 3 — Toques finos

10. **Selector de color de acento**
    - Personaliza orbe + panel
    - Sensación premium

11. **Acciones en respuesta**
    - "Copiar" y "Abrir en Obsidian"

12. **Diálogo Acerca de / versión**

---

## 🚨 Bug crítico ya arreglado

**Problema:** Conversaciones multi-turno se rompían (ej: portapapeles + título no funciona)  
**Causa:** Cada worker era nuevo, sin memoria de turnos previos  
**Solución:** Memoria conversacional persistente entre turnos, acotada a 16 turnos

**Ahora funciona:**
```
Tú: Crea una nota con mi portapapeles
LIA: ¿Qué título le pongo?
Tú: Ideas
LIA: (recuerda portapapeles) ✅ Nota "Ideas" creada
```

---

## 📌 Lo que falta (prioridad)

### Antes de Tier 1 — Verificación
- [x] **Vault apunta a `C:/LIAI`** — barra corregida en `.env` (la invertida podía romperse al parsear)
- [ ] **Probar memoria conversacional** — Repite los pasos del portapapeles

### Tier 1 (Quick wins)
- [x] #1 Icono en bandeja del sistema — mostrar/ocultar + **Salir** de verdad (`src/gui/tray_icon.py`)
- [x] #2 Onboarding de primer arranque — diálogo si falta clave/vault (`src/gui/onboarding.py`)
- [ ] #3 Errores elegantes
- [ ] #4 Log a fichero
- [ ] #5 Arranque con Windows (opcional)

### Tier 2 (Media jornada)
- [ ] #6 **Panel de Ajustes in-app** ⭐ (probablemente primero)
- [ ] #8 **Render Markdown en respuestas** ⭐ (visual impact)
- [ ] #7 Historial persistente
- [ ] #9 Captura rápida

### Tier 3 (Toques)
- [ ] #10 Color de acento
- [ ] #11 Acciones en respuesta
- [ ] #12 Acerca de

### Fase 5 (tras validar 4.5)
- [ ] Instalador `.exe`
- [ ] Arranque automático con Windows (integración más profunda)
- [ ] Distribución

---

## 🎯 Recomendación para arrancar

**Paquete "Se siente profesional"** (empezar por aquí):
1. Icono en bandeja (#1) — 1-2h, cierra la app de verdad
2. Onboarding (#2) — 1h, primera vez sin errores
3. Panel de Ajustes (#6) — 2-3h, la joya de la corona (sin `.env`)

Con estos tres, Lia pasa de "script en desarrollo" a "app lista para usar".

Luego (#8 Markdown) para el salto visual, y (#7 historial) si da tiempo.

---

## 🔍 Cómo testear ahora

```bash
# Memoria conversacional
LIA_PROACTIVE_DEBUG=1 python main.py
# → Abre panel
# → Di: "Crea una nota con mi portapapeles"
# → Di: "Ideas"
# → Debería crear nota con ese título

# Clustering
# → Crea 5+ notas sobre temas diferentes
# → Di: "¿Qué temas tengo en mis notas?"
# → Lia agrupa por significado

# Auto-tags
# → Crea nota: "Hablé con Ana sobre el proyecto Lia"
# → Obsidian → abre la nota
# → Debe tener tags: persona/Ana, proyecto/Lia, tema/conversación
```

---

## 📁 Estructura actual

```
src/
  core/
    orchestrator.py      — + memoria conversacional + reset
    state_manager.py
  services/
    gemini_service.py    — + history en ambos workers
    semantic_search.py
    semantic_index.py    — + get_matrix()
    topic_clusters.py    — Fase 3C
    daily_summary.py
  storage/
    obsidian_manager.py  — + normalize_tags()
  gui/
    orb_mascot.py        — Presencia única
    mascot_behavior.py   — Comportamiento ventana

tests/
  test_conversation_memory.py  — 4 tests (nueva)
  test_tags.py                 — 7 tests (nueva)
  test_clustering.py           — 5 tests (nueva)
  + 52 tests existentes

config/
  settings.py
  
.env
  OBSIDIAN_VAULT_PATH=C:\LIAI  ← donde escribe las notas
```

---

## 💡 Decisiones pendientes

- [ ] **Tier 2 #9 (Captura rápida)** — ¿Atajo global o desde el panel? ¿Con voz?
- [ ] **Color de acento** — ¿Paleta fija o selector libre?
- [ ] **Tiempos proactivos** — ¿Seguir con 30 min inactividad o ajustar?

