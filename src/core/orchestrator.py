import os
import logging
from typing import TYPE_CHECKING
import sounddevice as sd
from PyQt6.QtCore import QObject, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from config import settings
from src.core.state_manager import StateManager, AssistantState
from src.services.gemini_service import GeminiWorker, GeminiReasoningWorker
from src.services.os_automation import open_application
from src.io.audio_recorder import AudioRecorder
from src.services.whisper_local import TranscriptionWorker
from src.services.tts_service import TTSService
from src.services.system_monitor import SystemMonitor
from src.services.proactive_engine import ProactiveEngine
from src.gui.components.mascot_bubble import MascotBubble
from src.gui import styles
from config.paths import runtime_file
from config.logging_setup import friendly_error
from src.services.reminder_service import ReminderService
from src.services import conversation_store

if TYPE_CHECKING:
    from src.gui.view import View

class Orchestrator(QObject):
    """
    Mediator coordinating UI events, global keyboard shortcut triggers,
    state transitions, hardware audio recording, local Whisper STT,
    and background asynchronous Gemini API execution.
    """
    def __init__(self, view: "View", state_manager: StateManager, keyboard_listener, mascot=None):
        super().__init__()
        self.view = view
        self.state_manager = state_manager
        self.keyboard_listener = keyboard_listener
        self.mascot = mascot
        self.worker = None
        self.current_response_text = ""
        self._response_anchor = None   # posicion donde empieza la respuesta (para render markdown)
        self._pending_meta = None      # consumo de tokens, se muestra al final del turno
        self.history = []  # memoria conversacional (lista de types.Content) de la sesión

        # Setup QMediaPlayer for TTS responses
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Connect speech ready signal to playback handler
        TTSService.get_instance().speech_ready.connect(self.play_speech_audio)

        # Hardware Perception components
        self.audio_recorder = AudioRecorder()
        self.transcription_worker = None

        # Retrieve default microphone index
        try:
            self.active_mic_id = sd.default.device[0]  # Standard input device index
        except Exception:
            self.active_mic_id = None
            print("[Orchestrator] Advertencia: No se detectó ningún micrófono por defecto.")

        # Setup GUI & keyboard signaling pipelines
        self.keyboard_listener.hotkey_triggered.connect(self.toggle_ui)
        self.state_manager.state_changed.connect(self.on_state_changed)
        self.view.input_field.returnPressed.connect(self.handle_input_submission)

        # Wire settings config wheel and microphone recording buttons
        self.view.config_button.clicked.connect(self.open_settings)
        self.view.info_button.clicked.connect(self.show_info_menu)
        self.view.mic_button.clicked.connect(self.toggle_recording)

        # Wire audio recorder signals
        self.audio_recorder.recording_started.connect(self.on_recording_started)
        self.audio_recorder.recording_stopped.connect(self.on_recording_stopped)
        self.audio_recorder.error_occurred.connect(self.on_audio_error)

        # Wire the desktop mascot: un clic = hablar (abre panel + graba voz),
        # doble clic = abrir/cerrar el panel sin grabar.
        if self.mascot is not None:
            self.mascot.clicked.connect(self.on_orb_click)
            self.mascot.double_clicked.connect(self.toggle_ui)

        # --- Sistema proactivo (Fase 2): solo activo si hay mascota en escritorio ---
        self.system_monitor = None
        self.proactive_engine = None
        self.bubble = None
        self._pending_suggestion = ("", False)  # (prefill, auto_submit)

        # Recordatorios con hora -> aviso en la burbuja de la mascota
        self.reminder_service = ReminderService()
        self.reminder_service.reminder_due.connect(self.on_reminder_due)

        if self.mascot is not None and settings.proactive_enabled:
            debug = settings.proactive_debug
            # En modo debug los tiempos bajan a segundos para validar en vivo
            poll_ms = 1500 if debug else 4000
            self.system_monitor = SystemMonitor(poll_ms=poll_ms)
            if debug:
                self.proactive_engine = ProactiveEngine(
                    global_cooldown_s=8.0, note_gap_s=30.0,
                    focus_gap_s=30.0, eod_hour=0, debug=True,
                )
                print("[Orchestrator] Sistema proactivo en MODO DEBUG (tiempos cortos).")
            else:
                self.proactive_engine = ProactiveEngine()
            self.bubble = MascotBubble()

            # Monitor -> Motor
            self.system_monitor.clipboard_changed.connect(self.proactive_engine.on_clipboard_changed)
            self.system_monitor.active_window_changed.connect(self.proactive_engine.on_active_window_changed)
            self.system_monitor.tick.connect(self.proactive_engine.on_tick)

            # Motor -> UI (burbuja + expresión de la mascota)
            self.proactive_engine.suggestion.connect(self.on_proactive_suggestion)
            self.bubble.accepted.connect(self.on_suggestion_accepted)
            self.bubble.dismissed.connect(self.on_suggestion_dismissed)

    def show_welcome_greeting(self):
        """Muestra un saludo proactivo e inspirador en el display si está vacío, incitando a registrar ideas o tareas."""
        if not self.view.output_display.toPlainText().strip():
            import random
            greetings = [
                f"¡Hola {settings.user_name}! ¿Qué idea se te ha ocurrido hoy? 💡",
                f"Hola {settings.user_name}, ¿en qué tarea o proyecto profesional vamos a trabajar hoy? 🚀",
                "¡Buenas! Cuéntame, ¿qué hay de nuevo hoy en tus notas o estudios? 🧠",
                f"Hola {settings.user_name}, ¿tienes alguna idea o nota profesional para enlazar hoy? ✨",
                "¡Hola! ¿Qué se te pasa por la cabeza hoy? Estoy lista para anotarlo todo. 📝"
            ]
            greeting = random.choice(greetings)
            self.view.output_display.setHtml(
                f"<span style='color: #818CF8; font-weight: bold;'>LIA:</span> "
                f"<span style='color: #E8EAF2;'>{greeting}</span>"
            )

    def show_info_menu(self):
        """Muestra un menú desplegable con guías rápidas y ejemplos interactivos que autocompletan el input."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtCore import QPoint
        
        menu = QMenu(self.view)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(22, 16, 28, 0.96);
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 8px;
                color: #E8EAF2;
                padding: 4px;
                font-family: 'Segoe UI', 'Outfit', sans-serif;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 14px;
                background-color: transparent;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(99, 102, 241, 0.25);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(99, 102, 241, 0.2);
                margin: 4px 8px;
            }
        """)

        # Visión de pantalla
        vision_action = menu.addAction("📸 Ver Pantalla: \"Mira mi pantalla y resume...\"")
        vision_action.triggered.connect(lambda: self.view.input_field.setText("Mira mi pantalla y resume lo que ves."))

        # Portapapeles
        clip_action = menu.addAction("📋 Portapapeles: \"Crea una nota con mi portapapeles\"")
        clip_action.triggered.connect(lambda: self.view.input_field.setText("Crea una nota con lo que tengo en mi portapapeles."))

        # Cerebro
        brain_action = menu.addAction("🧠 Segundo Cerebro: \"Busca en mis notas...\"")
        brain_action.triggered.connect(lambda: self.view.input_field.setText("Busca en mis notas sobre "))

        # Separator
        menu.addSeparator()

        # Nueva conversación (olvida el historial)
        new_chat = menu.addAction("🆕 Nueva conversación")
        new_chat.triggered.connect(self.reset_conversation)

        # Cerrar LIA del todo (no depende del icono de la bandeja)
        quit_action = menu.addAction("🚪 Cerrar LIA")
        quit_action.triggered.connect(self.quit_app)

        # Help info item (non-clickable info)
        help_item = menu.addAction("🎙️ Micro: haz clic para hablar | Atajo: Shift_L + L")
        help_item.setEnabled(False)

        # Position menu right below the info button
        pos = self.view.info_button.mapToGlobal(QPoint(0, self.view.info_button.height()))
        menu.exec(pos)



    def start(self):
        """Starts the background listening thread and displays startup greeting."""
        self.keyboard_listener.start()
        if self.system_monitor is not None:
            self.system_monitor.start()
        # En modo debug, lanza una sugerencia de ejemplo a los 4s para ver el flujo
        if self.proactive_engine is not None and settings.proactive_debug:
            QTimer.singleShot(4000, self._show_demo_suggestion)
        self.reminder_service.start()
        self._restore_history()
        print("[Orchestrator] Sistema de LIA Assistant iniciado.")
        print("[Orchestrator] Presione 'Shift_L + L' globalmente para mostrar/ocultar el panel.")

    def on_orb_click(self):
        """Un clic en la bolita: abre el panel (si está oculto) y empieza a escuchar."""
        if not self.view.isVisible():
            self.view.show()
            self.view.raise_()
            self.view.activateWindow()
            self.show_welcome_greeting()
        # Empezar a grabar voz si no hay una consulta en curso ni grabación activa
        if (self.worker and self.worker.isRunning()) or self.audio_recorder.isRunning():
            self.view.input_field.setFocus()
            return
        self.toggle_recording()

    def toggle_ui(self):
        """Toggles the visibility of the frameless UI overlay window."""
        if self.view.isVisible():
            self.view.hide()
            self.state_manager.set_state(AssistantState.IDLE)
            print("[Orchestrator] Panel oculto. Estado: IDLE")
        else:
            self.view.show()
            self.view.raise_()
            self.view.activateWindow()
            self.view.input_field.setFocus()
            self.state_manager.set_state(AssistantState.LISTENING)
            self.show_welcome_greeting()
            print("[Orchestrator] Panel activado. Estado: LISTENING")

    def on_state_changed(self, state: AssistantState):
        """Maneja el comportamiento y la interfaz de usuario al cambiar de estado."""
        self.view.update_status_dot(state)

        # Reflejar el estado en la expresión de la mascota
        if self.mascot is not None:
            self.mascot.set_state(state)

        # Bloquear o desbloquear controles según el estado actual
        if state in (AssistantState.PROCESSING, AssistantState.RESPONDING):
            self.view.input_field.setEnabled(False)
            self.view.mic_button.setEnabled(False)
        else:
            self.view.mic_button.setEnabled(True)
            # Deshabilitar entrada de texto solo si el grabador de audio está activo
            is_recording = self.audio_recorder.isRunning()
            self.view.input_field.setEnabled(not is_recording)
            
            if state == AssistantState.IDLE:
                self.view.input_field.setFocus()

    def detect_reasoning_intent(self, text: str) -> bool:
        """
        Analiza si el texto ingresado por el usuario requiere el modelo Pro de razonamiento profundo
        (petición explícita de análisis a fondo, mentoría, consejo o decisión compleja),
        de lo contrario se usa el modelo Flash por velocidad y ahorro de tokens.
        """
        keywords = [
            "analiza a fondo", "analiza en profundidad", "razonamiento profundo",
            "razona", "consejo complejo", "decisión compleja", "mentoría", "reflexiona sobre"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def detect_vision_intent(self, text: str) -> bool:
        """
        Analiza si el texto ingresado requiere captura de pantalla como contexto visual.
        """
        keywords = [
            "pantalla", "pantallazo", "error", "consola", "mira", "ve", "captura",
            "visualiza", "abierto", "abierta", "codigo", "código", "portada", "interfaz"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def handle_input_submission(self):
        """Handles user text submission and spawns the background Gemini worker."""
        # Stop any ongoing speech before starting a new transaction
        self.player.stop()
        TTSService.get_instance().stop()
        self.current_response_text = ""
        self._response_anchor = None
        self._pending_meta = None

        # Prevent starting a new request if one is already running
        if self.worker and self.worker.isRunning():
            print("[Orchestrator] Advertencia: Ya hay una consulta en proceso.")
            return

        user_text = self.view.input_field.text().strip()
        if not user_text:
            return

        # Registrar actividad: el usuario interactuó con Lia (resetea inactividad)
        if self.proactive_engine is not None:
            self.proactive_engine.note_activity(is_capture=True)

        # Clear input field
        self.view.input_field.clear()

        # Update display logs
        self.view.output_display.append(f"<span style='color: #818CF8; font-weight: bold;'>Tú:</span> <span style='color: #E8EAF2;'>{user_text}</span>")
        self.view.output_display.append("<span style='color: #818CF8; font-weight: bold;'>LIA:</span> ")
        self.view.output_display.ensureCursorVisible()

        # Set UI state to processing
        self.state_manager.set_state(AssistantState.PROCESSING)

        # Capturar pantalla si el usuario tiene intención visual
        screenshot_path = None
        if self.detect_vision_intent(user_text):
            try:
                from PIL import ImageGrab
                screenshot_path = runtime_file("temp_screenshot.png")
                screenshot = ImageGrab.grab()
                screenshot.save(screenshot_path, "PNG")
                print(f"[Orchestrator] Capturando pantalla para contexto visual: {screenshot_path}")
            except Exception as e:
                print(f"[Orchestrator] Error al capturar pantalla: {e}")
                screenshot_path = None

        # Enrutar inteligentemente según la intención (pasando la memoria conversacional)
        if self.detect_reasoning_intent(user_text):
            print(f"[Orchestrator] Enrutando '{user_text}' al Agente de Razonamiento (Gemini Pro)...")
            self.worker = GeminiReasoningWorker(user_text, image_path=screenshot_path, history=self.history)
        else:
            print(f"[Orchestrator] Enrutando '{user_text}' al Agente de Acción Rápida (Gemini Flash)...")
            self.worker = GeminiWorker(user_text, image_path=screenshot_path, history=self.history)
        
        # Connect signals
        self.worker.token_received.connect(self.on_token_received)
        self.worker.tool_call_detected.connect(self.on_tool_call_detected)
        self.worker.tool_call_completed.connect(self.on_tool_call_completed)
        self.worker.tokens_consumed.connect(self.on_tokens_consumed)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.finished.connect(self.on_generation_finished)

        # Start background thread execution
        self.worker.start()

    def on_token_received(self, token: str):
        """Streams text tokens inline directly into the output display."""
        if self.state_manager.state == AssistantState.PROCESSING:
            self.state_manager.set_state(AssistantState.RESPONDING)

        if self._response_anchor is None:
            c = self.view.output_display.textCursor()
            c.movePosition(c.MoveOperation.End)
            self._response_anchor = c.position()

        self.current_response_text += token

        # Move text cursor to end and insert token inline (produces character-by-character animation)
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(token)
        self.view.output_display.ensureCursorVisible()

    def on_tool_call_detected(self, name: str, args: dict):
        """Muestra en consola que una herramienta está siendo ejecutada."""
        print(f"[Orchestrator - Tool Call] Detectado: {name} con argumentos {args}")

    def on_tool_call_completed(self, name: str, result: str):
        """Muestra en consola el resultado de la ejecución de la herramienta."""
        print(f"[Orchestrator - Tool Call] Completado: {name} -> {result}")

    def on_tokens_consumed(self, prompt_tokens: int, candidate_tokens: int, total_tokens: int):
        """Guarda el consumo de tokens para mostrarlo al final del turno."""
        self._pending_meta = (prompt_tokens, candidate_tokens, total_tokens)

    def on_error_occurred(self, err_msg: str):
        """Registra el error y muestra un mensaje humano en el panel."""
        logging.getLogger("lia").error("Error en worker: %s", err_msg)
        friendly = friendly_error(err_msg)
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: {styles.DANGER};'>{friendly}</span><br/>")
        self.view.output_display.ensureCursorVisible()

    def _trim_history(self, contents, max_items: int = 16):
        """
        Acota la memoria conversacional a los últimos `max_items` turnos para no
        disparar el consumo de tokens. Garantiza que el historial empiece por un
        turno 'user' (evita dejar una respuesta de herramienta sin su llamada).
        """
        trimmed = list(contents[-max_items:])
        while trimmed and getattr(trimmed[0], "role", None) != "user":
            trimmed.pop(0)
        return trimmed

    def reset_conversation(self):
        """Empieza una conversación nueva: olvida el historial y limpia el panel."""
        self.history = []
        conversation_store.clear()
        self.view.output_display.clear()
        self.show_welcome_greeting()

    def _history_to_turns(self, contents):
        """Serializa la conversación a [{role, text}] (ignora llamadas a herramientas)."""
        turns = []
        for c in contents:
            role = getattr(c, "role", None)
            if role not in ("user", "model"):
                continue
            text = "".join(getattr(part, "text", "") or "" for part in getattr(c, "parts", []))
            if text.strip():
                turns.append({"role": role, "text": text})
        return turns

    def _restore_history(self):
        """Recupera la conversación anterior (si existe) en memoria y en pantalla."""
        turns = conversation_store.load_turns()
        if not turns:
            self.show_welcome_greeting()
            return
        from google.genai import types
        self.history = [
            types.Content(role=t["role"], parts=[types.Part.from_text(text=t["text"])])
            for t in turns
        ]
        self._render_saved_history(turns)

    def _render_saved_history(self, turns):
        """Pinta los turnos recuperados en el panel (Lia con Markdown renderizado)."""
        import html as _html
        from src.gui.md_render import markdown_to_html
        blocks = []
        for t in turns:
            if t["role"] == "user":
                blocks.append(
                    f"<p><b style='color:{styles.ACCENT_BRIGHT}'>Tú:</b> "
                    f"<span style='color:{styles.TEXT}'>{_html.escape(t['text'])}</span></p>")
            else:
                blocks.append(
                    f"<p><b style='color:{styles.ACCENT_BRIGHT}'>LIA:</b> {markdown_to_html(t['text'])}</p>")
        self.view.output_display.setHtml("".join(blocks))

    def on_reminder_due(self, texto: str):
        """Un recordatorio vencido: avisa con la burbuja de la mascota."""
        logging.getLogger("lia").info("Recordatorio vencido: %s", texto)
        if self.mascot is None:
            return
        if self.bubble is None:
            self.bubble = MascotBubble()
        from src.gui.mascot_behavior import MascotMood
        self.mascot.set_mood(MascotMood.REMINDER)
        self.bubble.show_message(f"⏰ Recordatorio: {texto}", self.mascot, with_actions=False)

    def quit_app(self):
        """Cierra LIA por completo: detiene los hilos de fondo y mata el proceso."""
        print("[Orchestrator] Cerrando LIA...")
        try:
            self.keyboard_listener.stop()
        except Exception:
            pass
        try:
            if self.system_monitor is not None:
                self.system_monitor.stop()
        except Exception:
            pass
        try:
            self.reminder_service.stop()
        except Exception:
            pass
        try:
            TTSService.get_instance().stop()
        except Exception:
            pass
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
        # Red de seguridad: si algun hilo nativo (pynput/Win32) impide salir,
        # forzamos el cierre del proceso al poco tiempo.
        QTimer.singleShot(600, lambda: os._exit(0))

    def on_generation_finished(self):
        """Restores the UI state to idle when the generation ends."""
        self.state_manager.set_state(AssistantState.IDLE)

        # Render Markdown: sustituye el texto plano transmitido por su HTML
        self.view.output_display.finalize_response(self._response_anchor, self.current_response_text)
        self._response_anchor = None

        # Mostrar el consumo de tokens al final del turno
        if self._pending_meta:
            p, c, t = self._pending_meta
            cursor = self.view.output_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertHtml(
                f"<br/><span style='color: {styles.TEXT_DIM}; font-size: 11px; font-style: italic;'>"
                f"[Tokens · entrada {p} · salida {c} · total {t}]</span><br/>"
            )
            self._pending_meta = None
            self.view.output_display.ensureCursorVisible()

        # Trigger text to speech on the generated text
        if self.current_response_text:
            TTSService.get_instance().speak(self.current_response_text)

        # Conserva la conversación actualizada (memoria entre turnos), acotada
        if self.worker and getattr(self.worker, "result_contents", None):
            self.history = self._trim_history(self.worker.result_contents)
            conversation_store.save_turns(self._history_to_turns(self.history))

        # Safely mark QThread for garbage collection
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

        # Clean up screenshot if it exists
        _shot = runtime_file("temp_screenshot.png")
        if os.path.exists(_shot):
            try:
                os.remove(_shot)
            except Exception as e:
                print(f"[Orchestrator] Error al eliminar temp_screenshot.png: {e}")

    # --- Sistema Proactivo (Fase 2) ---

    def _show_demo_suggestion(self):
        """[debug] Muestra una sugerencia de ejemplo para validar el flujo visual."""
        self.on_proactive_suggestion(
            f"¡Hola {settings.user_name}! Soy Lia. Cuando vea algo que merezca la "
            f"pena anotar, te avisaré así. ¿Probamos a crear una nota?",
            "Crea una nota de prueba titulada 'Mi primera nota con Lia'.",
            False, "reminder",
        )

    def on_proactive_suggestion(self, text: str, prefill: str, auto_submit: bool, mood: str):
        """Muestra una sugerencia proactiva de Lia mediante la burbuja de la mascota."""
        # No interrumpir si el panel está abierto o Lia está ocupada
        if self.view.isVisible() or (self.worker and self.worker.isRunning()):
            return
        if self.audio_recorder.isRunning():
            return

        self._pending_suggestion = (prefill, auto_submit)
        if self.mascot is not None:
            self.mascot.set_mood(mood)
            self.bubble.show_message(text, self.mascot, with_actions=True)

    def on_suggestion_accepted(self):
        """El usuario aceptó la sugerencia: abre el panel y precarga/ejecuta la acción."""
        prefill, auto_submit = self._pending_suggestion
        self._pending_suggestion = ("", False)
        if self.proactive_engine is not None:
            self.proactive_engine.record_feedback(True)

        if not self.view.isVisible():
            self.toggle_ui()

        if prefill:
            self.view.input_field.setText(prefill)
            if auto_submit:
                self.handle_input_submission()
            else:
                self.view.input_field.setFocus()

    def on_suggestion_dismissed(self):
        """El usuario descartó la sugerencia (o expiró). Reduce la insistencia."""
        self._pending_suggestion = ("", False)
        if self.proactive_engine is not None:
            self.proactive_engine.record_feedback(False)
        if self.mascot is not None:
            from src.gui.mascot_behavior import MascotMood
            self.mascot.set_mood(MascotMood.IDLE)

    # --- Hardware Audio & STT Handlers ---

    def toggle_recording(self):
        """Starts or stops hardware recording based on current worker state."""
        # Ignore mic interaction if we are currently waiting for LLM responses
        if self.worker and self.worker.isRunning():
            return

        if self.audio_recorder.isRunning():
            # Stop the audio recorder (this triggers recording_stopped)
            self.audio_recorder.stop_recording()
        else:
            # Pass selected device index and start recording
            self.audio_recorder.set_device(self.active_mic_id)
            self.audio_recorder.start()

    def on_recording_started(self):
        """Handles visual UI feedback when microphone recording starts."""
        self.player.stop()
        TTSService.get_instance().stop()
        self.state_manager.set_state(AssistantState.LISTENING)
        self.view.set_recording_active(True)
        print("[Orchestrator] Capturando audio desde micrófono...")

    def on_recording_stopped(self, audio_path: str):
        """Transitions state and triggers background Whisper transcription when audio is ready."""
        self.view.set_recording_active(False)
        self.state_manager.set_state(AssistantState.PROCESSING)

        # Notify user on UI
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        prefix = "" if not self.view.output_display.toPlainText().strip() else "<br/>"
        cursor.insertHtml(f"{prefix}<span style='color: #F59E0B;'><i>[LIA: Procesando grabación de voz...]</i></span>")
        self.view.output_display.ensureCursorVisible()

        # Launch background transcription QThread
        self.transcription_worker = TranscriptionWorker(audio_path)
        self.transcription_worker.transcription_completed.connect(self.on_transcription_completed)
        self.transcription_worker.error_occurred.connect(self.on_transcription_error)
        self.transcription_worker.start()

    def on_transcription_completed(self, text: str):
        """Fills in the user text and auto-submits once transcription completes."""
        if self.transcription_worker:
            self.transcription_worker.deleteLater()
            self.transcription_worker = None

        if not text:
            # Fallback to idle if silence or audio couldn't resolve
            cursor = self.view.output_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            prefix = "" if not self.view.output_display.toPlainText().strip() else "<br/>"
            cursor.insertHtml(f"{prefix}<span style='color: #F87171;'><i>[LIA: No se detectó voz clara. Intente de nuevo.]</i></span>")
            self.view.output_display.ensureCursorVisible()
            self.state_manager.set_state(AssistantState.IDLE)
            return

        # Write transcribed query to input and trigger submission
        self.view.input_field.setText(text)
        self.handle_input_submission()

    def on_transcription_error(self, err_msg: str):
        """Cleans transcription worker reference and calls base error handler."""
        if self.transcription_worker:
            self.transcription_worker.deleteLater()
            self.transcription_worker = None
        self.on_audio_error(err_msg)

    def on_audio_error(self, err_msg: str):
        """Displays audio errors on UI and resets state."""
        logging.getLogger("lia").warning("Error de audio: %s", err_msg)
        self.view.set_recording_active(False)
        self.state_manager.set_state(AssistantState.IDLE)

        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #F87171;'><b>Error de Audio:</b> {err_msg}</span><br/>")
        self.view.output_display.ensureCursorVisible()

    def open_settings(self):
        """Abre el panel de Ajustes (perfil, conexion, voz y microfono)."""
        from PyQt6.QtWidgets import QDialog
        from src.gui.onboarding import OnboardingDialog, apply_config
        dlg = OnboardingDialog(
            current_name=settings.user_name if settings.user_name != "Usuario" else "",
            current_key=settings.gemini_api_key or "",
            current_vault=str(settings.obsidian_vault_path or ""),
            mic_devices=self._list_microphones(),
            current_mic=self.active_mic_id,
            tts_enabled=TTSService.get_instance().enabled,
            parent=self.view,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        apply_config(settings, v["name"], v["key"], v["vault"])
        if v.get("tts") is not None:
            TTSService.get_instance().set_enabled(v["tts"])
        if v.get("mic_id") is not None:
            self.active_mic_id = v["mic_id"]
        # Refrescar el saludo con el nuevo nombre si el panel esta vacio
        if not self.view.output_display.toPlainText().strip():
            self.show_welcome_greeting()

    def _list_microphones(self):
        """Devuelve [(id, nombre)] de los microfonos de entrada disponibles."""
        devices = []
        try:
            seen = set()
            for idx, dev in enumerate(sd.query_devices()):
                if dev.get('max_input_channels', 0) > 0:
                    name = dev.get('name', f"Microfono {idx}")
                    if name not in seen:
                        seen.add(name)
                        devices.append((idx, name))
        except Exception as e:
            print(f"[Orchestrator] Error al listar microfonos: {e}")
        return devices

    def show_config_menu(self):
        """Queries connected input devices and requests view to spawn selector QMenu."""
        try:
            # Query active hardware devices
            devices = sd.query_devices()
            input_devices = []
            seen_names = set()
            for idx, dev in enumerate(devices):
                if dev.get('max_input_channels', 0) > 0:
                    name = dev.get('name', f"Micrófono {idx}")
                    if name not in seen_names:
                        seen_names.add(name)
                        input_devices.append((idx, name))

            # Retrieve active status of TTS
            tts_enabled = TTSService.get_instance().enabled

            # Display the selection dropdown in the view
            self.view.show_config_menu(
                input_devices,
                self.active_mic_id,
                tts_enabled,
                self.toggle_tts,
                self.select_microphone
            )
        except Exception as e:
            print(f"[Orchestrator] Error al listar los micrófonos del sistema: {e}")

    def toggle_tts(self):
        """Toggles the active state of TTS service and logs status on UI."""
        service = TTSService.get_instance()
        new_state = not service.enabled
        service.set_enabled(new_state)

        status_msg = "activada" if new_state else "desactivada"
        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #818CF8;'><i>[Sistema: Respuesta por voz {status_msg}]</i></span><br/>")
        self.view.output_display.ensureCursorVisible()
        print(f"[Orchestrator] Respuesta por voz (TTS) cambiada a: {new_state}")

    def select_microphone(self, device_id):
        """Updates active microphone configuration index and logs status on UI."""
        self.active_mic_id = device_id
        
        try:
            info = sd.query_devices(device_id, 'input')
            name = info.get('name', f"Dispositivo {device_id}")
        except Exception:
            name = f"Dispositivo {device_id}"

        cursor = self.view.output_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(f"<br/><span style='color: #818CF8;'><i>[Sistema: Micrófono activo cambiado a '{name}']</i></span><br/>")
        self.view.output_display.ensureCursorVisible()
        print(f"[Orchestrator] Micrófono de entrada cambiado a ID {device_id} ({name})")

    def play_speech_audio(self, path: str):
        """Plays the generated speech MP3 file using QMediaPlayer."""
        if os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
