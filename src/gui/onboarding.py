"""
Onboarding de primer arranque.

Si falta la clave de Gemini o la ruta del vault, en vez de arrancar roto en
silencio (y reventar al enviar el primer mensaje), mostramos un diálogo amable
para configurarlo. Lo escribe en `.env` y actualiza los settings en memoria.
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog,
)
from PyQt6.QtCore import Qt

# .env en la raíz del proyecto (robusto sin importar el cwd)
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
    """Diálogo simple para introducir la clave de Gemini y la ruta del vault."""

    def __init__(self, current_key: str = "", current_vault: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar LIA")
        self.setModal(True)
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        intro = QLabel(
            "¡Hola! Antes de empezar necesito dos datos.\n"
            "Puedes cambiarlos más tarde en tu archivo .env."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Clave de Gemini
        layout.addWidget(QLabel("Clave de la API de Gemini:"))
        self.key_input = QLineEdit(current_key)
        self.key_input.setPlaceholderText("AQ.xxxxxxxx…")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)

        # Ruta del vault
        layout.addWidget(QLabel("Carpeta del vault de Obsidian:"))
        vault_row = QHBoxLayout()
        self.vault_input = QLineEdit(current_vault)
        self.vault_input.setPlaceholderText("C:/LIAI")
        vault_row.addWidget(self.vault_input)
        browse = QPushButton("Examinar…")
        browse.clicked.connect(self._browse_vault)
        vault_row.addWidget(browse)
        layout.addLayout(vault_row)

        # Aviso de validación
        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #F87171;")
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)

        # Botones
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("Guardar")
        save.setDefault(True)
        save.clicked.connect(self._on_save)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _browse_vault(self):
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta del vault")
        if folder:
            self.vault_input.setText(folder)

    def _on_save(self):
        key = self.key_input.text().strip()
        vault = self.vault_input.text().strip().replace("\\", "/")
        if not key:
            self.warning.setText("Falta la clave de la API de Gemini.")
            return
        if not vault:
            self.warning.setText("Falta la carpeta del vault.")
            return
        self._key = key
        self._vault = vault
        self.accept()

    def values(self):
        return self._key, self._vault


def ensure_configured(settings) -> bool:
    """
    Garantiza que hay clave de Gemini y ruta de vault. Si faltan, abre el
    onboarding. Devuelve True si la app puede continuar, False si el usuario
    canceló sin completar la configuración.
    """
    has_key = bool(settings.gemini_api_key)
    has_vault = bool(settings.obsidian_vault_path)
    if has_key and has_vault:
        return True

    dialog = OnboardingDialog(
        current_key=settings.gemini_api_key or "",
        current_vault=str(settings.obsidian_vault_path or ""),
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    key, vault = dialog.values()
    _upsert_env({"GEMINI_API_KEY": key, "OBSIDIAN_VAULT_PATH": vault})

    # Actualizar los settings en memoria para este arranque
    settings.gemini_api_key = key
    settings.obsidian_vault_path = Path(vault)
    return True
