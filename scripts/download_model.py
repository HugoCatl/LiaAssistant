"""
Descarga un modelo Live2D Cubism 3 completo (parsea su .model3.json y baja todos
los assets referenciados) dentro de ./models/<nombre>/.

Uso:
    python scripts/download_model.py                      # modelo por defecto (Haru)
    python scripts/download_model.py --url <model3.json>  # cualquier modelo Cubism 3
    python scripts/download_model.py --url ... --name lia_gato

Tras descargarlo, main.py lo detecta automáticamente (busca en ./models/**), o
puedes fijarlo explícitamente con la variable de entorno LIA:
    LIVE2D_MODEL_PATH=models/<nombre>/<archivo>.model3.json

Fuentes de modelos gratis:
  - Gatos oficiales (Tororo / Hijiki): https://www.live2d.com/en/learn/sample/
  - Colecciones: https://github.com/Eikanya/Live2d-model
NOTA: live2d.v3 requiere modelos Cubism 3 (.model3.json), no Cubism 2 (.model.json).
"""
import argparse
import json
import os
import sys
import urllib.request

DEFAULT_URL = (
    "https://cdn.jsdelivr.net/gh/Auto-SK/Live2D-Models/tororo/model.json"
)


def _download(url: str, dest: str) -> bool:
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        print(f"  [ok] {os.path.relpath(dest)}")
        return True
    except Exception as e:
        print(f"  [x]  {url}  ({e})")
        return False


def _collect_files(manifest: dict) -> list:
    """
    Extrae las rutas relativas referenciadas, soportando ambos esquemas:
      - Cubism 3: claves dentro de "FileReferences" (Moc, Textures, Motions[*].File...)
      - Cubism 2: claves en la raíz en minúscula (model, textures, motions[*].file...)
    """
    files = []
    refs = manifest.get("FileReferences")

    if refs is not None:  # Cubism 3
        for key in ("Moc", "Physics", "Pose", "DisplayInfo"):
            if refs.get(key):
                files.append(refs[key])
        files.extend(refs.get("Textures", []) or [])
        for exp in refs.get("Expressions", []) or []:
            if exp.get("File"):
                files.append(exp["File"])
        for group in (refs.get("Motions", {}) or {}).values():
            for m in group:
                if m.get("File"):
                    files.append(m["File"])
                if m.get("Sound"):
                    files.append(m["Sound"])
    else:  # Cubism 2
        for key in ("model", "physics", "pose"):
            if manifest.get(key):
                files.append(manifest[key])
        files.extend(manifest.get("textures", []) or [])
        for exp in manifest.get("expressions", []) or []:
            if exp.get("file"):
                files.append(exp["file"])
        for group in (manifest.get("motions", {}) or {}).values():
            for m in group:
                if m.get("file"):
                    files.append(m["file"])
                if m.get("sound"):
                    files.append(m["sound"])

    # quita duplicados conservando el orden
    seen, out = set(), []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def main():
    parser = argparse.ArgumentParser(description="Descarga un modelo Live2D Cubism 3.")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL del .model3.json")
    parser.add_argument("--name", default=None, help="Nombre de la carpeta destino")
    args = parser.parse_args()

    base_url = args.url.rsplit("/", 1)[0] + "/"
    model_file = args.url.rsplit("/", 1)[1]
    # Nombre de carpeta: --name, o el nombre del archivo, o la carpeta padre de la URL
    # (los Cubism 2 usan un genérico "model.json", así que tomamos la carpeta padre).
    stem = model_file.replace(".model3.json", "").replace(".model.json", "")
    if stem in ("model", "") or model_file == "model.json":
        stem = base_url.rstrip("/").rsplit("/", 1)[-1]
    name = args.name or stem

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest_dir = os.path.join(root, "models", name)
    model_dest = os.path.join(dest_dir, model_file)

    print(f"Descargando modelo «{name}» desde:\n  {args.url}\n")
    if not _download(args.url, model_dest):
        print("\nNo se pudo descargar el .model3.json. Revisa la URL.")
        sys.exit(1)

    with open(model_dest, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    files = _collect_files(manifest)

    print(f"\nDescargando {len(files)} assets referenciados...")
    ok = 0
    for rel in files:
        rel_norm = rel.replace("\\", "/")
        if _download(base_url + rel_norm, os.path.join(dest_dir, rel_norm)):
            ok += 1

    print(f"\nListo: {ok}/{len(files)} assets. Modelo en:\n  {os.path.relpath(model_dest)}")
    print("\nArranca la app y Lia usará este modelo automáticamente:")
    print("  venv\\Scripts\\python.exe main.py")


if __name__ == "__main__":
    main()
