"""Reglas independientes de OpenCV para poder probar cruces y revisiones."""
from dataclasses import asdict, dataclass, field
import csv
import json
import math
from pathlib import Path
from statistics import median

from .config import Config
from .assignment import minimum_assignment

CATEGORIES = ("adulto", "becerro", "pendiente")


@dataclass
class Event:
    id: int
    track_id: int
    timestamp_seconds: float
    category: str
    automatic_category: str
    height_cm: float | None
    reason: str
    reviewed: bool = False


class Ledger:
    def __init__(self, count_only=False):
        self.count_only = count_only
        self.events = []
        self.revisions = []

    @property
    def totals(self):
        if self.count_only:
            return {"total": len(self.events)}
        return {"total": len(self.events), **{c: sum(e.category == c for e in self.events) for c in CATEGORIES}}

    def add(self, track_id, timestamp, category, height, reason):
        if category not in (("bovino",) if self.count_only else CATEGORIES):
            raise ValueError("Categoria invalida.")
        event = Event(len(self.events) + 1, track_id, timestamp, category, category, height, reason)
        self.events.append(event)
        return event

    def review(self, event_id, category, method, timestamp):
        if self.count_only:
            raise ValueError("Esta sesion solo registra cruces de bovinos.")
        if category not in CATEGORIES:
            raise ValueError("Categoria invalida.")
        event = next((e for e in self.events if e.id == event_id), None)
        if event is None:
            raise ValueError("Evento inexistente.")
        # Una orden sostenida o repetida no crea revisiones duplicadas.
        if event.reviewed and event.category == category:
            return False
        self.revisions.append(dict(event_id=event_id, before=event.category, after=category,
                                   method=method, timestamp_seconds=timestamp, total=len(self.events)))
        event.category, event.reviewed = category, True
        return True

    def save(self, directory, metadata):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        data = dict(schema_version=1, metadata=metadata, totals=self.totals,
                    events=[asdict(e) for e in self.events], revisions=self.revisions)
        temp = directory / "session.json.tmp"
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(directory / "session.json")
        temp_csv = directory / "events.csv.tmp"
        with temp_csv.open("w", newline="", encoding="utf-8-sig") as output:
            writer = csv.DictWriter(output, fieldnames=list(Event.__dataclass_fields__))
            writer.writeheader()
            writer.writerows(asdict(e) for e in self.events)
        temp_csv.replace(directory / "events.csv")

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Version de sesion no admitida.")
        ledger = cls(count_only=data["metadata"].get("count_only", False))
        ledger.events = [Event(**event) for event in data["events"]]
        if len({e.id for e in ledger.events}) != len(ledger.events):
            raise ValueError("IDs de eventos duplicados.")
        categories = ("bovino",) if ledger.count_only else CATEGORIES
        if any(e.category not in categories or e.automatic_category not in categories for e in ledger.events):
            raise ValueError("Categoria de sesion invalida.")
        ledger.revisions = data["revisions"]
        return ledger, data["metadata"]


@dataclass
class Detection:
    # Unidades normalizadas en el fotograma completo.
    x: float
    y: float
    box: tuple
    top_y: float | None = None
    keypoints: dict = field(default_factory=dict)
    confidence: float | None = None


@dataclass
class Track:
    id: int
    detection: Detection
    last_seen: float
    armed: bool = False
    counted: bool = False
    heights: list = field(default_factory=list)
    velocity_x: float = 0.0
    velocity_y: float = 0.0


def classify(heights, config):
    if config.reference_height_cm is None:
        return "pendiente", None, "sin_calibracion"
    if len(heights) < config.min_height_samples:
        return "pendiente", None, "evidencia_insuficiente"
    height = median(heights)
    distance = abs(height - config.adult_threshold_cm)
    if distance <= config.uncertainty_cm or math.isclose(distance, config.uncertainty_cm, abs_tol=1e-9):
        return "pendiente", height, "intervalo_de_duda"
    return ("adulto" if height > config.adult_threshold_cm else "becerro"), height, "altura_calibrada"


class Counter:
    def __init__(self, config: Config, ledger=None):
        self.config = config
        self.ledger = ledger if ledger is not None else Ledger()
        self.tracks = {}
        self.next_id = 1
        self.timestamp = 0.0

    def _sample(self, track, detection):
        if self.ledger.count_only:
            return
        c = self.config
        # Solo medir alrededor de B; descartar lomo oculto y recortes.
        if detection.top_y is None or c.reference_height_cm is None:
            return
        if abs(detection.x - c.line_b) > abs(c.line_b - c.line_a) / 2:
            return
        height = (c.ground_y - detection.top_y) * c.reference_height_cm / (c.ground_y - c.reference_top_y)
        if height > 0 and math.isfinite(height):
            track.heights.append(height)
            track.heights[:] = track.heights[-30:]

    def update(self, detections, timestamp):
        c = self.config
        self.timestamp = timestamp
        self.tracks = {k: t for k, t in self.tracks.items() if timestamp - t.last_seen <= c.max_missing_seconds}
        # En modo pose: asignación global con predicción breve de movimiento y anatomía.
        # En modo movimiento se conserva la asociación original para compatibilidad.
        if detections and any(d.keypoints for d in detections) and self.tracks:
            ids = list(self.tracks)
            costs = []
            for tid in ids:
                t = self.tracks[tid]
                dt = min(max(timestamp - t.last_seen, 0), 0.25)
                px, py = t.detection.x + t.velocity_x * dt, t.detection.y + t.velocity_y * dt
                row = []
                for d in detections:
                    distance = math.hypot(px - d.x, py - d.y)
                    observed = math.hypot(t.detection.x - d.x, t.detection.y - d.y)
                    if min(distance, observed) > c.max_distance_ratio:
                        row.append(1e6)
                        continue
                    anatomy = []
                    for key in ("nose", "neck", "tail_root"):
                        old, new = t.detection.keypoints.get(key), d.keypoints.get(key)
                        if old and new and min(old[2], new[2]) >= c.pose_confidence:
                            anatomy.append(math.hypot(old[0] + t.velocity_x * dt - new[0],
                                                      old[1] + t.velocity_y * dt - new[1]))
                    row.append(distance + (0.2 * sum(anatomy) / len(anatomy) if anatomy else 0))
                costs.append(row + [c.max_distance_ratio * 1.5] * len(ids))
            pairs = [(costs[r][col], ids[r], col) for r, col in minimum_assignment(costs)
                     if col < len(detections) and costs[r][col] < 1e5]
        else:
            pairs = sorted((math.hypot(t.detection.x - d.x, t.detection.y - d.y), tid, i)
                           for tid, t in self.tracks.items() for i, d in enumerate(detections))
        used_tracks, used_detections = set(), set()
        created = []
        for distance, tid, index in pairs:
            if (not detections[index].keypoints and distance > c.max_distance_ratio) or tid in used_tracks or index in used_detections:
                continue
            track, detection = self.tracks[tid], detections[index]
            previous = track.detection.x * c.sign
            position = detection.x * c.sign
            a, b = c.line_a * c.sign, c.line_b * c.sign
            self._sample(track, detection)
            if not track.counted:
                if previous < a <= position:
                    track.armed = True
                elif position < a:
                    track.armed = False
                if track.armed and previous < b <= position:
                    category, height, reason = ("bovino", None, "cruce") if self.ledger.count_only else classify(track.heights, c)
                    created.append(self.ledger.add(tid, timestamp, category, height, reason))
                    track.counted = True
            elapsed = timestamp - track.last_seen
            if elapsed > 0:
                track.velocity_x = 0.6 * (detection.x - track.detection.x) / elapsed + 0.4 * track.velocity_x
                track.velocity_y = 0.6 * (detection.y - track.detection.y) / elapsed + 0.4 * track.velocity_y
            track.detection, track.last_seen = detection, timestamp
            used_tracks.add(tid)
            used_detections.add(index)
        for i, detection in enumerate(detections):
            if i not in used_detections:
                track = Track(self.next_id, detection, timestamp)
                self._sample(track, detection)
                self.tracks[self.next_id] = track
                self.next_id += 1
        return created


class GestureLatch:
    """Un gesto estable por selección; soltar la mano antes de otra orden."""
    def __init__(self, hold_seconds=0.7, release_seconds=0.4):
        self.hold = hold_seconds
        self.release = release_seconds
        self.candidate = None
        self.since = 0.0
        self.latched = False
        self.release_since = None

    def update(self, category, selection, now):
        key = (selection, category) if selection is not None and category is not None else None
        if self.latched:
            if category is None:
                if self.release_since is None:
                    self.release_since = now
                if now - self.release_since >= self.release:
                    self.latched = False
                    self.candidate = None
            else:
                self.release_since = None
            return None
        if key != self.candidate:
            self.candidate, self.since = key, now
        if key is not None and now - self.since >= self.hold:
            self.latched = True
            self.release_since = None
            return category
        return None
