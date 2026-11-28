from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path


@dataclass
class Config:
    # Coordenadas normalizadas respecto al fotograma completo.
    roi: tuple = (0.05, 0.1, 0.9, 0.8)  # x, y, ancho, alto
    line_a: float = 0.35
    line_b: float = 0.65
    direction: str = "right"
    warmup_frames: int = 30
    min_area_ratio: float = 0.005
    max_area_ratio: float = 0.65
    max_distance_ratio: float = 0.15
    max_missing_seconds: float = 2.0
    min_height_samples: int = 3
    ground_y: float | None = None
    reference_top_y: float | None = None
    reference_height_cm: float | None = None
    adult_threshold_cm: float | None = None
    uncertainty_cm: float = 10.0
    gesture_hold_seconds: float = 0.7
    gesture_release_seconds: float = 0.4
    detector_confidence: float = 0.35
    pose_confidence: float = 0.30
    pose_detail_pass: bool = False

    def validate(self):
        numeric = [v for v in asdict(self).values() if isinstance(v, (int, float))]
        if any(not math.isfinite(v) for v in numeric):
            raise ValueError("La configuracion debe contener numeros finitos.")
        if len(self.roi) != 4 or not all(isinstance(v, (float, int)) and math.isfinite(v) for v in self.roi):
            raise ValueError("ROI debe contener x, y, ancho y alto numericos.")
        x, y, w, h = self.roi
        if not (0 <= x < 1 and 0 <= y < 1 and w > 0 and h > 0 and x + w <= 1 and y + h <= 1):
            raise ValueError("ROI fuera del fotograma.")
        if not (x < self.line_a < x + w and x < self.line_b < x + w):
            raise ValueError("Las dos lineas deben estar dentro de la ROI.")
        if self.direction not in ("right", "left"):
            raise ValueError("direction debe ser right o left.")
        if (self.line_b - self.line_a) * self.sign <= 0:
            raise ValueError("A debe estar antes de B en el sentido de avance.")
        if not 0 < self.min_area_ratio < self.max_area_ratio <= 1:
            raise ValueError("Los limites de area deben cumplir 0 < min < max <= 1.")
        if not 0 < self.max_distance_ratio <= 1 or self.max_missing_seconds <= 0:
            raise ValueError("Distancia y tiempo de seguimiento invalidos.")
        if self.warmup_frames < 1 or self.min_height_samples < 1:
            raise ValueError("Se requiere al menos un fotograma de fondo y una muestra de altura.")
        if any(not isinstance(v, int) or isinstance(v, bool) for v in (self.warmup_frames, self.min_height_samples)):
            raise ValueError("Los numeros de fotogramas y muestras deben ser enteros.")
        calibration = (self.ground_y, self.reference_top_y, self.reference_height_cm, self.adult_threshold_cm)
        if any(v is not None for v in calibration):
            if any(v is None for v in calibration):
                raise ValueError("La calibracion debe estar completa o ser toda null.")
            if not (y <= self.reference_top_y < self.ground_y <= y + h):
                raise ValueError("La referencia y el suelo deben estar dentro de la ROI.")
            if self.reference_height_cm <= 0 or self.adult_threshold_cm <= 0:
                raise ValueError("Las alturas deben ser positivas.")
        if self.uncertainty_cm < 0 or self.gesture_hold_seconds <= 0 or self.gesture_release_seconds <= 0:
            raise ValueError("Margen de duda y tiempos de gesto invalidos.")
        if not (0 < self.detector_confidence <= 1 and 0 < self.pose_confidence <= 1):
            raise ValueError("Los umbrales de deteccion y pose deben estar entre 0 y 1.")
        if not isinstance(self.pose_detail_pass, bool):
            raise ValueError("pose_detail_pass debe ser booleano.")
        return self

    @property
    def sign(self):
        return 1 if self.direction == "right" else -1

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path=None):
        if not path:
            return cls().validate()
        return cls(**json.loads(Path(path).read_text(encoding="utf-8"))).validate()
