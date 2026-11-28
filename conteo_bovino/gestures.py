"""MediaPipe Tasks Hands. La captura del operador es independiente del corral."""
import math
from pathlib import Path


def gesture_category(landmarks):
    if len(landmarks) != 21:
        return None
    # Dedos índice, medio, anular y meñique; pulgar ignorado.
    # Distancia 3D y ángulo evitan depender de la orientación izquierda/derecha.
    def extended(mcp, pip, tip):
        a, b, c = landmarks[mcp], landmarks[pip], landmarks[tip]
        u = (a.x - b.x, a.y - b.y, a.z - b.z)
        v = (c.x - b.x, c.y - b.y, c.z - b.z)
        norm = math.sqrt(sum(x*x for x in u) * sum(x*x for x in v))
        if norm <= 1e-12:
            return False
        cosine = sum(x*y for x, y in zip(u, v)) / norm
        wrist = landmarks[0]
        distance = lambda p: (p.x - wrist.x)**2 + (p.y - wrist.y)**2 + (p.z - wrist.z)**2
        return cosine < -0.65 and distance(c) > distance(b) * 1.15

    fingers = tuple(extended(*indices) for indices in ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)))
    return {(True, False, False, False): "adulto", (True, True, False, False): "becerro",
            (True, True, True, True): "pendiente"}.get(fingers)


class Hands:
    def __init__(self, model_path):
        import mediapipe as mp
        self.mp = mp
        if not Path(model_path).is_file():
            raise ValueError("Falta el modelo de manos; ejecuta python scripts/download_hand_model.py.")
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(Path(model_path).resolve())),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
        )
        self.detector = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self.last_timestamp = -1

    def detect(self, bgr, timestamp_ms):
        import cv2
        import numpy as np
        timestamp_ms = max(self.last_timestamp + 1, int(timestamp_ms))
        self.last_timestamp = timestamp_ms
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB,
                              data=np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
        result = self.detector.detect_for_video(image, timestamp_ms)
        # Dos manos en imagen se consideran ambiguas.
        if len(result.hand_landmarks) != 1:
            return None
        return gesture_category(result.hand_landmarks[0])

    def close(self):
        self.detector.close()
