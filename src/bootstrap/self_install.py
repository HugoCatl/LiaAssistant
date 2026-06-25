"""
Auto-instalación en el primer arranque (solo para el .exe congelado).

Objetivo: que el usuario haga UN solo doble clic. Si LIA.exe se ejecuta desde
fuera de su carpeta de instalación (p. ej. Descargas), se copia a
%LOCALAPPDATA%\\Programs\\LIA, crea accesos directos (escritorio + menú inicio) y
se registra en "Agregar o quitar programas". Es idempotente y silencioso: en los
siguientes arranques (ya desde su carpeta) no hace nada.

No toca nada en desarrollo (solo actúa si sys.frozen).
"""
import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

_CREATE_NO_WINDOW = 0x08000000  # evita abrir una consola de PowerShell


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "Programs" / "LIA"


def _current_exe() -> Path:
    return Path(sys.executable)


def is_installed() -> bool:
    """True si ya nos estamos ejecutando desde la carpeta de instalación."""
    try:
        return _current_exe().resolve() == (install_dir() / "LIA.exe").resolve()
    except Exception:
        return False


def ensure_installed():
    """
    Copia el exe a su carpeta, crea accesos directos y lo registra. Idempotente.
    Devuelve la ruta instalada, o None si no aplica (desarrollo / ya instalado) o falla.
    """
    if not is_frozen() or is_installed():
        return None
    try:
        dest_dir = install_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / "LIA.exe"
        shutil.copy2(_current_exe(), target)
        _run_powershell(_install_script(target))
        return target
    except Exception:
        return None


def _install_script(target: Path) -> str:
    exe = str(target)
    work = str(target.parent)
    desktop = os.path.join(os.environ.get("USERPROFILE", str(Path.home())), "Desktop")
    start = os.path.join(
        os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
    uninst = str(target.parent / "Desinstalar-LIA.ps1")
    return f'''
$ErrorActionPreference = "SilentlyContinue"
$ws = New-Object -ComObject WScript.Shell
function New-Lnk($p) {{
  $l = $ws.CreateShortcut($p)
  $l.TargetPath = "{exe}"
  $l.WorkingDirectory = "{work}"
  $l.IconLocation = "{exe}"
  $l.Description = "LIA Assistant"
  $l.Save()
}}
New-Lnk "{desktop}\\LIA.lnk"
New-Lnk "{start}\\LIA.lnk"

# Desinstalador
@"
`$ErrorActionPreference = 'SilentlyContinue'
Remove-Item '{desktop}\\LIA.lnk' -Force
Remove-Item '{start}\\LIA.lnk' -Force
Remove-Item 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\LIA' -Recurse -Force
Start-Sleep 1
Remove-Item '{work}' -Recurse -Force
"@ | Set-Content -Encoding UTF8 "{uninst}"

# Registro en "Agregar o quitar programas" (HKCU, sin admin)
$key = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\LIA"
New-Item -Path $key -Force | Out-Null
Set-ItemProperty $key DisplayName "LIA Assistant"
Set-ItemProperty $key DisplayIcon "{exe}"
Set-ItemProperty $key DisplayVersion "1.0"
Set-ItemProperty $key Publisher "Hugo Catalan"
Set-ItemProperty $key InstallLocation "{work}"
Set-ItemProperty $key UninstallString "powershell -NoProfile -ExecutionPolicy Bypass -File `"{uninst}`""
Set-ItemProperty $key NoModify 1
Set-ItemProperty $key NoRepair 1
'''


def _run_powershell(script: str):
    """Ejecuta un script de PowerShell efímero, sin abrir ventana."""
    f = tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8")
    try:
        f.write(script)
        f.close()
        flags = _CREATE_NO_WINDOW if sys.platform == "win32" else 0
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", f.name],
            creationflags=flags, timeout=30,
        )
    finally:
        try:
            os.remove(f.name)
        except Exception:
            pass
