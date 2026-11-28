"""Descarga explícita del modelo oficial de MediaPipe; nunca durante el conteo."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="models/hand_landmarker.task")
    args = parser.parse_args()
    path = Path(args.output)
    if path.exists():
        raise SystemExit(f"El modelo ya existe: {path}. No se sobrescribio.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".download")
    try:
        with urllib.request.urlopen(URL, timeout=60) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if temporary.stat().st_size < 1024:
            raise ValueError("Descarga incompleta.")
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(path)
        path.with_suffix(".metadata.json").write_text(json.dumps(dict(url=URL, sha256=digest), indent=2) + "\n", encoding="utf-8")
        print(f"Modelo guardado: {path.resolve()}\nSHA256: {digest}")
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
