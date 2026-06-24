"""
Genera packaging/lia.ico: un orbe morado con degradado radial, a juego con la
mascota de LIA. Se ejecuta antes de PyInstaller (lo hace build.bat).
"""
import math
import os

from PIL import Image


def make_icon(path: str, size: int = 256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx = cy = size / 2.0
    r = size * 0.46

    # Degradado radial: lila claro en el centro -> violeta en el borde
    light = (216, 180, 254)
    dark = (124, 58, 237)

    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= r:
                t = dist / r
                rr = int(light[0] + (dark[0] - light[0]) * t)
                gg = int(light[1] + (dark[1] - light[1]) * t)
                bb = int(light[2] + (dark[2] - light[2]) * t)
                # Antialias del borde
                edge = max(0.0, min(1.0, (r - dist)))
                a = int(255 * (edge if dist > r - 1 else 1.0))
                px[x, y] = (rr, gg, bb, a)

    img.save(path, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icono generado: {path}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    make_icon(os.path.join(here, "lia.ico"))
