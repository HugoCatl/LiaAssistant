"""Renderiza la mascota gato Lia en varios moods/poses a un PNG de previsualización."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)

from src.gui.mascot import MascotWidget, MascotMood, _Pose

moods = [
    MascotMood.IDLE, MascotMood.CURIOUS, MascotMood.REMINDER,
    MascotMood.LISTENING, MascotMood.THINKING, MascotMood.SPEAKING,
]

W, H = MascotWidget.WIDGET_W, MascotWidget.WIDGET_H
cols = len(moods)
sheet = QPixmap(W * cols, H * 2)
sheet.fill(QColor("#1a1320"))

p = QPainter(sheet)
# Fila 1: sentado, cada mood
for i, mood in enumerate(moods):
    w = MascotWidget()
    w._mood = mood; w._pose = _Pose.SIT; w._facing = 1
    w._phase = 0.6; w._wave_phase = 1.2
    pm = QPixmap(W, H); pm.fill(Qt.GlobalColor.transparent)
    w.render(pm)
    p.drawPixmap(i * W, 0, pm)

# Fila 2: caminando, dos frames del ciclo, en idle, ambas direcciones + sentado idle
walk_frames = [
    (_Pose.WALK, 1, 0.0), (_Pose.WALK, 1, 1.6),
    (_Pose.WALK, -1, 0.8), (_Pose.WALK, -1, 2.4),
    (_Pose.SIT, -1, 0.6), (_Pose.SIT, 1, 3.0),
]
for i, (pose, facing, lp) in enumerate(walk_frames):
    w = MascotWidget()
    w._mood = MascotMood.IDLE; w._pose = pose; w._facing = facing
    w._phase = 0.6; w._wave_phase = 1.2; w._leg_phase = lp
    pm = QPixmap(W, H); pm.fill(Qt.GlobalColor.transparent)
    w.render(pm)
    p.drawPixmap(i * W, H, pm)
p.end()

out = "scripts/mascot_preview.png"
sheet.save(out, "PNG")
print(f"OK: preview guardada en {out}")
