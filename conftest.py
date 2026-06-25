"""Configuración compartida de pytest.

Fuerza el backend offscreen de Qt y provee una única QApplication para los tests
de interfaz, de modo que se puedan instanciar widgets sin pantalla.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Por defecto, sin enlazado automático en tests (evita cargar fastembed). Los
# tests que lo prueban lo reactivan con monkeypatch e inyectan un índice stub.
os.environ.setdefault("LIA_DISABLE_AUTOLINK", "1")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
