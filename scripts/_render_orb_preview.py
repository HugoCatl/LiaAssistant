"""Renderiza el orbe de Lia en cada estado a un PNG de previsualización."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)

from src.gui.orb_mascot import OrbMascot
from src.gui.mascot_behavior import MascotMood

moods = [
    MascotMood.IDLE, MascotMood.CURIOUS, MascotMood.REMINDER,
    MascotMood.LISTENING, MascotMood.THINKING, MascotMood.SPEAKING,
]

W, H = OrbMascot.WIDGET_W, OrbMascot.WIDGET_H
sheet = QPixmap(W * len(moods), H)
sheet.fill(QColor("#1a1320"))  # fondo oscuro tipo escritorio

p = QPainter(sheet)
for i, mood in enumerate(moods):
    w = OrbMascot()
    w._mood = mood
    w._breath = 1.0; w._spin = 0.8; w._fx = 1.4
    pm = QPixmap(W, H); pm.fill(Qt.GlobalColor.transparent)
    w.render(pm)
    p.drawPixmap(i * W, 0, pm)
p.end()

out = "scripts/orb_preview.png"
sheet.save(out, "PNG")
print(f"OK: preview guardada en {out}")
