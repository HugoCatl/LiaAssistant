# 📈 LIA — Estado del proyecto

> Documento vivo. Para el "qué hace" ver [README.md](README.md); para el "cómo está hecho" ver [ARQUITECTURA.md](ARQUITECTURA.md).

## Resumen

LIA está **funcionalmente completa** y se distribuye como **un único `.exe` autoinstalable**. ~100 pruebas en verde.

---

## ✅ Hecho

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

**Captura y voz**
- Voz (Whisper local), visión de pantalla, TTS (Edge), automatización del SO.
- Enrutamiento Flash/Pro.

**Producto**
- Onboarding plug-and-play (nombre, clave, carpeta que se crea sola).
- `.exe` autoinstalable (PyInstaller) que se copia, crea accesos directos y se registra.
- Config y estado aislados en `%LOCALAPPDATA%/LiaAssistant`.

---

## ⏳ Pendiente / ideas

- **Captura rápida**: atajo global → escribir → Enter guarda sin abrir conversación.
- **Toques**: color de acento configurable; acciones "Copiar" / "Abrir en Obsidian" en cada burbuja; diálogo "Acerca de".
- **Distribución pro**: firmar el `.exe` (quita el aviso de SmartScreen, ~300 €/año); opción de LLM local para privacidad total.

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
