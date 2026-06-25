"""Tests de la auto-instalación (sin tocar el sistema real: todo mockeado)."""
from pathlib import Path

import src.bootstrap.self_install as si


def test_noop_in_dev_mode(monkeypatch, tmp_path):
    """Sin sys.frozen (desarrollo) no debe instalar nada."""
    monkeypatch.setattr(si, "is_frozen", lambda: False)
    called = []
    monkeypatch.setattr(si, "_run_powershell", lambda s: called.append(s))
    assert si.ensure_installed() is None
    assert called == []


def test_copies_exe_and_runs_script(monkeypatch, tmp_path):
    """En modo .exe y fuera de su carpeta: copia el exe y lanza el script de accesos."""
    src_exe = tmp_path / "src" / "LIA.exe"
    src_exe.parent.mkdir(parents=True)
    src_exe.write_bytes(b"fake-exe")
    dest = tmp_path / "install"

    monkeypatch.setattr(si, "is_frozen", lambda: True)
    monkeypatch.setattr(si, "_current_exe", lambda: src_exe)
    monkeypatch.setattr(si, "install_dir", lambda: dest)
    scripts = []
    monkeypatch.setattr(si, "_run_powershell", lambda s: scripts.append(s))

    result = si.ensure_installed()
    assert result == dest / "LIA.exe"
    assert (dest / "LIA.exe").read_bytes() == b"fake-exe"
    assert len(scripts) == 1
    # El script crea accesos directos y registra la desinstalación
    assert "LIA.lnk" in scripts[0]
    assert "Uninstall\\LIA" in scripts[0]


def test_skips_when_already_installed(monkeypatch, tmp_path):
    """Si ya se ejecuta desde la carpeta de instalación, no reinstala."""
    dest = tmp_path / "install"
    dest.mkdir()
    installed_exe = dest / "LIA.exe"
    installed_exe.write_bytes(b"x")

    monkeypatch.setattr(si, "is_frozen", lambda: True)
    monkeypatch.setattr(si, "install_dir", lambda: dest)
    monkeypatch.setattr(si, "_current_exe", lambda: installed_exe)
    called = []
    monkeypatch.setattr(si, "_run_powershell", lambda s: called.append(s))

    assert si.is_installed() is True
    assert si.ensure_installed() is None
    assert called == []


def test_install_script_has_real_paths(monkeypatch, tmp_path):
    target = tmp_path / "Programs" / "LIA" / "LIA.exe"
    script = si._install_script(target)
    assert str(target) in script
    assert "WScript.Shell" in script
    assert "DisplayName" in script
