"""Modelos ONNX oficiales; descarga explícita y comprobación SHA256."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

MODELS = {
    "yolox_s.onnx": (
        "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/object_detection_yolox/object_detection_yolox_2022nov.onnx",
        "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063"),
    "rtmpose_ap10k.zip": (
        "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206.zip",
        "2d75445331cf2f21d6e164430f96ffa765cd874872965ae1736932dda03987f0"),
}


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="models/animal_pose")
    args = parser.parse_args()
    base = Path(args.output)
    base.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (url, expected) in MODELS.items():
        path = base / name
        if not path.exists():
            temporary = path.with_suffix(".download")
            with urllib.request.urlopen(url, timeout=60) as source, temporary.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            if sha256(temporary) != expected:
                raise ValueError(f"Hash incorrecto: {name}")
            temporary.replace(path)
        if sha256(path) != expected:
            raise ValueError(f"El archivo local no coincide con el modelo fijado: {name}")
        manifest[name] = dict(url=url, sha256=expected, size=path.stat().st_size)
        print(f"Verificado: {name}")
    # Extraer solo la red, sin ejecutar contenido del paquete ni usar sus rutas.
    target = base / "rtmpose_ap10k.onnx"
    with zipfile.ZipFile(base / "rtmpose_ap10k.zip") as archive:
        candidates = [name for name in archive.namelist() if name.endswith("/end2end.onnx")]
        if len(candidates) != 1:
            raise ValueError("El paquete no contiene una unica red de pose.")
        if not target.exists():
            with archive.open(candidates[0]) as source, target.with_suffix(".extract").open("wb") as destination:
                shutil.copyfileobj(source, destination)
            target.with_suffix(".extract").replace(target)
        with archive.open(candidates[0]) as source:
            expected = hashlib.file_digest(source, "sha256").hexdigest()
        if sha256(target) != expected:
            raise ValueError("La red extraida no coincide con el paquete oficial.")
        manifest[target.name] = dict(sha256=expected, extracted_from="rtmpose_ap10k.zip")
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
