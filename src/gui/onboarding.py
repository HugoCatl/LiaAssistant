"""
Onboarding / Ajustes de LIA.

Mismo dialogo para dos usos:
  - Primer arranque (ensure_configured): pide lo minimo (nombre, clave, vault).
  - Ajustes (open desde la rueda): ademas permite TTS on/off y elegir microfono.

Guarda en .env: USER_NAME, USER_PROFILE, GEMINI_API_KEY y OBSIDIAN_VAULT_PATH.
USER_PROFILE = nombre, para que la nota de perfil en Obsidian se llame como tu
(antes se quedaba como 'Usuario').
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QFrame, QGraphicsDropShadowEffect,
    QCheckBox, QComboBox,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor

from src.gui import styles
from config.paths import env_path

_ENV_PATH = env_path()


def _default_vault() -> str:
    """Carpeta sugerida para el vault: Documentos/LIA (se crea al guardar)."""
    return str(Path.home() / "Documents" / "LIA").replace("\\", "/")


def _upsert_env(updates: dict):
    """Crea o actualiza claves en .env conservando el resto del archivo."""
    path = env_path()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    done = set()
    for i, line in enumerate(lines):
        s = line.strip()
        if "=" in s and not s.startswith("#"):
            key = s.split("=", 1)[0].strip()
            if key in updates:
                lines[i] = f"{key}={updates[key]}"
                done.add(key)
    for key, value in updates.items():
        if key not in done:
            lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _section(text, parent):
    lbl = QLabel(text.upper(), parent)
    lbl.setStyleSheet(
        "QLabel { color: %s; font-family: %s; font-size: 10px; font-weight: 700;"
        " letter-spacing: 2px; background: transparent; }" % (styles.ACCENT_SOFT, styles.FONT))
    return lbl


class OnboardingDialog(QDialog):
    """Dialogo de configuracion/ajustes con la identidad indigo."""

    def __init__(self, current_name="", current_key="", current_vault="",
                 mic_devices=None, current_mic=None, tts_enabled=None, parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()
        self._settings_mode = mic_devices is not None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        card = QFrame(self)
        card.setObjectName("GlassCard")
        card.setStyleSheet(styles.card_style())
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(40, 45, 90, 150))
        shadow.setOffset(0, 3)
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(26, 22, 26, 22)
        lay.setSpacing(7)

        title = QLabel("AJUSTES" if self._settings_mode else "TE DOY LA BIENVENIDA", card)
        title.setStyleSheet(styles.title_style(16))
        lay.addWidget(title)
        if not self._settings_mode:
            subtitle = QLabel(
                "Soy Lia, tu segundo cerebro de escritorio. Dime cómo te llamas, pega tu "
                "clave de Gemini y elige dónde guardaré tus notas. Listo en 20 segundos.",
                card,
            )
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet(
                "QLabel { color: %s; font-family: %s; font-size: 12px;"
                " background: transparent; }" % (styles.TEXT_DIM, styles.FONT))
            lay.addWidget(subtitle)
        lay.addSpacing(4)

        # --- Perfil ---
        lay.addWidget(_section("Perfil", card))
        lay.addWidget(self._field_label("Tu nombre", card))
        self.name_input = QLineEdit(current_name, card)
        self.name_input.setPlaceholderText("Tu nombre")
        self.name_input.setStyleSheet(styles.input_style())
        lay.addWidget(self.name_input)
        lay.addSpacing(8)

        # --- Conexion ---
        lay.addWidget(_section("Conexión", card))
        lay.addWidget(self._field_label("Clave de la API de Gemini", card))
        self.key_input = QLineEdit(current_key, card)
        self.key_input.setPlaceholderText("AQ.xxxxxxxx...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setStyleSheet(styles.input_style())
        lay.addWidget(self.key_input)
        if not self._settings_mode:
            hint = QLabel("¿No tienes clave? Es gratis en aistudio.google.com/apikey", card)
            hint.setStyleSheet(
                "QLabel { color: %s; font-family: %s; font-size: 10px;"
                " background: transparent; }" % (styles.TEXT_DIM, styles.FONT))
            lay.addWidget(hint)
        lay.addSpacing(4)

        lay.addWidget(self._field_label("Carpeta donde Lia guardará tus notas", card))
        vault_row = QHBoxLayout()
        vault_row.setSpacing(8)
        self.vault_input = QLineEdit(current_vault or _default_vault(), card)
        self.vault_input.setPlaceholderText(_default_vault())
        self.vault_input.setStyleSheet(styles.input_style())
        vault_row.addWidget(self.vault_input)
        browse = QPushButton("Examinar...", card)
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.setStyleSheet(styles.secondary_button_style())
        browse.clicked.connect(self._browse_vault)
        vault_row.addWidget(browse)
        lay.addLayout(vault_row)

        # --- Voz y microfono (solo en modo ajustes) ---
        self.tts_check = None
        self.mic_combo = None
        if self._settings_mode:
            lay.addSpacing(8)
            lay.addWidget(_section("Voz y micrófono", card))
            self.tts_check = QCheckBox("Respuesta por voz (TTS)", card)
            self.tts_check.setChecked(bool(tts_enabled))
            self.tts_check.setCursor(Qt.CursorShape.PointingHandCursor)
            self.tts_check.setStyleSheet(
                "QCheckBox { color: %s; font-family: %s; font-size: 12px; spacing: 8px;"
                " background: transparent; }"
                " QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px;"
                " border: 1px solid rgba(255,255,255,0.25); background: %s; }"
                " QCheckBox::indicator:checked { background: %s; border: 1px solid %s; }"
                % (styles.TEXT, styles.FONT, styles.INPUT_BG, styles.ACCENT, styles.ACCENT))
            lay.addWidget(self.tts_check)
            lay.addSpacing(4)
            lay.addWidget(self._field_label("Micrófono", card))
            self.mic_combo = QComboBox(card)
            self.mic_combo.setCursor(Qt.CursorShape.PointingHandCursor)
            self.mic_combo.setStyleSheet(
                "QComboBox { background: %s; border: 1px solid rgba(255,255,255,0.12);"
                " border-radius: 9px; color: %s; padding: 7px 10px; font-size: 12px;"
                " font-family: %s; }"
                " QComboBox:focus { border: 1px solid %s; }"
                " QComboBox::drop-down { border: none; width: 22px; }"
                " QComboBox QAbstractItemView { background: #14161C; color: %s;"
                " selection-background-color: rgba(99,102,241,0.35);"
                " border: 1px solid %s; }"
                % (styles.INPUT_BG, styles.TEXT, styles.FONT, styles.ACCENT,
                   styles.TEXT, styles.CARD_BORDER))
            for dev_id, dev_name in (mic_devices or []):
                self.mic_combo.addItem(dev_name, dev_id)
            if current_mic is not None:
                idx = self.mic_combo.findData(current_mic)
                if idx >= 0:
                    self.mic_combo.setCurrentIndex(idx)
            lay.addWidget(self.mic_combo)

        # Aviso de validacion
        self.warning = QLabel("", card)
        self.warning.setStyleSheet(
            "color: %s; font-family: %s; font-size: 11px; background: transparent;" % (styles.DANGER, styles.FONT))
        self.warning.setWordWrap(True)
        lay.addSpacing(6)
        lay.addWidget(self.warning)

        # Botones
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar", card)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(styles.secondary_button_style())
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("Guardar", card)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setStyleSheet(styles.primary_button_style())
        save.setDefault(True)
        save.clicked.connect(self._on_save)
        buttons.addWidget(save)
        lay.addLayout(buttons)

        self._result = None

    def _field_label(self, text, parent):
        lbl = QLabel(text, parent)
        lbl.setStyleSheet(styles.label_style())
        return lbl

    def _browse_vault(self):
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta del vault")
        if folder:
            self.vault_input.setText(folder)

    def _on_save(self):
        name = self.name_input.text().strip()
        key = self.key_input.text().strip()
        vault = self.vault_input.text().strip().replace("\\", "/")
        if not key:
            self.warning.setText("Falta la clave de la API de Gemini.")
            return
        if not vault:
            self.warning.setText("Falta la carpeta donde guardar las notas.")
            return
        # Crear la carpeta si no existe (plug & play: el usuario no la prepara a mano)
        try:
            Path(vault).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.warning.setText(f"No pude crear la carpeta: {e}")
            return
        self._result = {
            "name": name or "Usuario",
            "key": key,
            "vault": vault,
            "tts": self.tts_check.isChecked() if self.tts_check else None,
            "mic_id": self.mic_combo.currentData() if self.mic_combo else None,
        }
        self.accept()

    def values(self) -> dict:
        return self._result or {}

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


def apply_config(settings, name, key, vault):
    """Persiste perfil/conexion en .env y en los settings en memoria.

    USER_PROFILE = name para que la nota de perfil de Obsidian se llame como el
    usuario (corrige el bug del nodo 'Usuario').
    """
    _upsert_env({
        "USER_NAME": name,
        "USER_PROFILE": name,
        "GEMINI_API_KEY": key,
        "OBSIDIAN_VAULT_PATH": vault,
    })
    settings.user_name = name
    settings.user_profile = name
    settings.gemini_api_key = key
    settings.obsidian_vault_path = Path(vault)


def ensure_configured(settings) -> bool:
    """Primer arranque: si falta clave o vault, abre el dialogo. True si continua."""
    if settings.gemini_api_key and settings.obsidian_vault_path:
        return True
    dialog = OnboardingDialog(
        current_name=settings.user_name if settings.user_name != "Usuario" else "",
        current_key=settings.gemini_api_key or "",
        current_vault=str(settings.obsidian_vault_path or ""),
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    v = dialog.values()
    apply_config(settings, v["name"], v["key"], v["vault"])
    return True


def open_config(settings) -> bool:
    """Ajustes basicos desde la bandeja (sin micro/TTS)."""
    dialog = OnboardingDialog(
        current_name=settings.user_name if settings.user_name != "Usuario" else "",
        current_key=settings.gemini_api_key or "",
        current_vault=str(settings.obsidian_vault_path or ""),
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    v = dialog.values()
    apply_config(settings, v["name"], v["key"], v["vault"])
    return True
