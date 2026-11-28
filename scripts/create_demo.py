"""Crea un video SINTETICO para probar la tuberia, no la precision con ganado."""
import argparse
from pathlib import Path
import cv2
import numpy as np


def create_demo(path):
    path = Path(path)
    if path.exists():
        raise ValueError(f"Ya existe: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (640, 360))
    if not writer.isOpened():
        raise ValueError("No se pudo crear el video de prueba.")
    frames = 0

    def frame(center=None, top=100):
        nonlocal frames
        image = np.full((360, 640, 3), 30, dtype=np.uint8)
        if center is not None:
            cv2.rectangle(image, (center - 35, top), (center + 35, 290), (220, 220, 220), -1)
        writer.write(image)
        frames += 1

    try:
        for _ in range(45):
            frame()
        # Cruce 1, con una pausa de 2 s entre A y B.
        for center in range(70, 571, 5):
            frame(center)
            if center == 300:
                for _ in range(60):
                    frame(center)
        for _ in range(90):
            frame()
        # Intento cancelado: cruza A y retrocede sin llegar a B.
        for center in list(range(70, 301, 5)) + list(range(295, 69, -5)):
            frame(center, 180)
        for _ in range(90):
            frame()
        # Cruce 2, más bajo; la clasificación sigue pendiente sin calibración.
        for center in range(70, 571, 5):
            frame(center, 180)
        for _ in range(90):
            frame()
    finally:
        writer.release()
    return frames


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="assets/demo_sintetico.avi")
    args = parser.parse_args()
    print(f"Fotogramas: {create_demo(args.output)}")
