"""
Onboarding / configuracion de LIA.

Si falta la clave de Gemini o la ruta del vault, en vez de arrancar roto en
silencio, mostramos un dialogo elegante para configurarlo. Tambien se puede
abrir en cualquier momento desde la bandeja ("Configurar...").

Guarda en .env: USER_NAME, GEMINI_API_KEY y OBSIDIAN_VAULT_PATH, y actualiza
los settings en memoria para el arranque actual.
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QFrame, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor

from src.gui import styles

# .env en la raiz del proyecto (robusto sin importar el cwd)
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _upsert_env(updates: dict):
    """Crea o actualiza claves en .env conservando el resto del archivo."""
    lines = []
    if _ENV_PATH.exists():
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()

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

    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


class OnboardingDialog(QDialog):
    """Dialogo glassmorphic para configurar nombre, clave de Gemini y vault."""

    def __init__(self, current_name="", current_key="", current_vault="", parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)

        card = QFrame(self)
        card.setObjectName("GlassCard")
        card.setStyleSheet(styles.card_style())
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(192, 132, 252, 70))
        shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(8)

        title = QLabel("CONFIGURA LIA", card)
        title.setStyleSheet(styles.title_style(16))
        layout.addWidget(title)

        intro = QLabel(
            "Solo necesito un par de datos para empezar.\n"
            "Podras cambiarlos cuando quieras desde la bandeja.", card
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(styles.label_style(dim=True))
        layout.addWidget(intro)
        layout.addSpacing(8)

        layout.addWidget(self._field_label("Tu nombre", card))
        self.name_input = QLineEdit(current_name, card)
        self.name_input.setPlaceholderText("Hugo")
        self.name_input.setStyleSheet(styles.input_style())
        layout.addWidget(self.name_input)
        layout.addSpacing(6)

        layout.addWidget(self._field_label("Clave de la API de Gemini", card))
        self.key_input = QLineEdit(current_key, card)
        self.key_input.setPlaceholderText("AQ.xxxxxxxx...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setStyleSheet(styles.input_style())
        layout.addWidget(self.key_input)
        layout.addSpacing(6)

        layout.addWidget(self._field_label("Carpeta del vault de Obsidian", card))
        vault_row = QHBoxLayout()
        vault_row.setSpacing(8)
        self.vault_input = QLineEdit(current_vault, card)
        self.vault_input.setPlaceholderText("C:/LIAI")
        self.vault_input.setStyleSheet(styles.input_style())
        vault_row.addWidget(self.vault_input)
        browse = QPushButton("Examinar...", card)
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.setStyleSheet(styles.secondary_button_style())
        browse.clicked.connect(self._browse_vault)
        vault_row.addWidget(browse)
        layout.addLayout(vault_row)

        self.warning = QLabel("", card)
        self.warning.setStyleSheet("color: #F87171; font-family: %s; font-size: 11px;" % styles.FONT)
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)
        layout.addSpacing(6)

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
        layout.addLayout(buttons)

        self._name = current_name
        self._key = current_key
        self._vault = current_vault

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
            self.warning.setText("Falta la carpeta del vault.")
            return
        self._name = name or "Usuario"
        self._key = key
        self._vault = vault
        self.accept()

    def values(self):
        return self._name, self._key, self._vault

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


def _apply(settings, name, key, vault):
    """Persiste en .env y actualiza los settings en memoria."""
    _upsert_env({"USER_NAME": name, "GEMINI_API_KEY": key, "OBSIDIAN_VAULT_PATH": vault})
    settings.user_name = name
    settings.gemini_api_key = key
    settings.obsidian_vault_path = Path(vault)


def ensure_configured(settings) -> bool:
    """
    Garantiza clave de Gemini + ruta de vault. Si faltan, abre el onboarding.
    Devuelve True si la app puede continuar, False si se cancelo.
    """
    if settings.gemini_api_key and settings.obsidian_vault_path:
        return True

    dialog = OnboardingDialog(
        current_name=settings.user_name or "",
        current_key=settings.gemini_api_key or "",
        current_vault=str(settings.obsidian_vault_path or ""),
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    _apply(settings, *dialog.values())
    return True


def open_config(settings) -> bool:
    """
    Abre el dialogo de configuracion SIEMPRE (desde la bandeja), prerelleno con
    los valores actuales. Devuelve True si se guardo.
    """
    dialog = OnboardingDialog(
        current_name=settings.user_name or "",
        current_key=settings.gemini_api_key or "",
        current_vault=str(settings.obsidian_vault_path or ""),
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    _apply(settings, *dialog.values())
    return True
