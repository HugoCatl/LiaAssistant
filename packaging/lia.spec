# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller para empaquetar LIA en un único LIA.exe (onefile, sin consola).

Uso (desde Windows, con el venv del proyecto activado):
    pyinstaller --noconfirm --clean packaging/lia.spec

Notas:
- Los modelos de faster-whisper y fastembed NO se empaquetan: se descargan a la
  caché del usuario la primera vez que se usan (mantiene el .exe más ligero).
- El .env NO se incluye a propósito (lleva tu clave). En el primer arranque el
  onboarding lo crea. Si quieres distribuir con valores por defecto, añade
  .env.example a `datas`.
"""
import os
from PyInstaller.utils.hooks import (
    collect_all, collect_submodules, collect_dynamic_libs,
)

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = []
binaries = []
hiddenimports = []

# Paquetes con datos/DLLs/submódulos que PyInstaller no detecta solo
for pkg in [
    "fastembed", "onnxruntime", "faster_whisper", "ctranslate2",
    "tokenizers", "google", "google.genai", "edge_tts", "huggingface_hub",
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# DLL de PortAudio para sounddevice
try:
    binaries += collect_dynamic_libs("sounddevice")
except Exception:
    pass

hiddenimports += collect_submodules("pynput")

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PySide6", "PyQt5"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="LIA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # app de escritorio, sin ventana de consola
    disable_windowed_traceback=False,
    icon=os.path.join(SPECPATH, "lia.ico"),
)
