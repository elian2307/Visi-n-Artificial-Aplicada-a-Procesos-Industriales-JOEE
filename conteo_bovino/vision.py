import cv2
import numpy as np

from .core import Detection


class MotionDetector:
    def __init__(self, config):
        self.config = config
        self.background = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=32, detectShadows=True)
        self.frames = 0
        self.mask = None

    def detect(self, frame, occupied=False):
        c = self.config
        height, width = frame.shape[:2]
        x, y, w, h = c.roi
        left, top = int(x * width), int(y * height)
        right, bottom = int((x + w) * width), int((y + h) * height)
        region = frame[top:bottom, left:right]
        if min(region.shape[:2]) < 5:
            raise ValueError("ROI demasiado pequena para este video.")
        warming = self.frames < c.warmup_frames
        # Congelar el fondo durante un seguimiento conserva animales detenidos.
        rate = -1 if warming else (0 if occupied else 0.002)
        mask = self.background.apply(cv2.GaussianBlur(region, (5, 5), 0), learningRate=rate)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        self.mask = mask
        self.frames += 1
        if warming:
            return []
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections = []
        area = region.shape[0] * region.shape[1]
        for contour in contours:
            if not c.min_area_ratio * area <= cv2.contourArea(contour) <= c.max_area_ratio * area:
                continue
            bx, by, bw, bh = cv2.boundingRect(contour)
            box = ((left + bx) / width, (top + by) / height, bw / width, bh / height)
            # Lomo aproximado: mediana del borde superior de columnas centrales.
            tops = []
            if bx > 1 and by > 1 and bx + bw < region.shape[1] - 1 and by + bh < region.shape[0] - 1:
                for column in range(bx + bw // 3, bx + 2 * bw // 3):
                    foreground = np.flatnonzero(mask[by:by + bh, column])
                    if foreground.size:
                        tops.append((top + by + int(foreground[0])) / height)
            top_y = float(np.median(tops)) if len(tops) >= 3 else None
            detections.append(Detection(box[0] + box[2] / 2, box[1] + box[3] / 2, box, top_y))
        return detections


def create_detector(config, kind="motion", model_dir="models/animal_pose"):
    if kind == "pose":
        from .animal_pose import CattlePoseDetector
        return CattlePoseDetector(config, model_dir)
    return MotionDetector(config)


def draw(frame, counter, selected, warming=False, paused=False):
    c = counter.config
    height, width = frame.shape[:2]
    x, y, w, h = c.roi
    cv2.rectangle(frame, (int(x * width), int(y * height)), (int((x + w) * width), int((y + h) * height)), (255, 180, 0), 2)
    for name, line, color in (("A", c.line_a, (0, 200, 255)), ("B", c.line_b, (0, 255, 0))):
        px = int(line * width)
        cv2.line(frame, (px, int(y * height)), (px, int((y + h) * height)), color, 2)
        cv2.putText(frame, name, (px + 5, int(y * height) + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    for track in counter.tracks.values():
        if track.last_seen < counter.timestamp - 1e-6:
            continue  # Retener ID durante oclusiones, sin dibujar puntos viejos como observaciones.
        bx, by, bw, bh = track.detection.box
        color = ((track.id * 67) % 180 + 60, (track.id * 97) % 180 + 60, (track.id * 43) % 180 + 60) if track.detection.keypoints else ((0, 255, 0) if track.counted else (255, 200, 0))
        cv2.rectangle(frame, (int(bx * width), int(by * height)), (int((bx + bw) * width), int((by + bh) * height)), color, 2)
        suffix = " OK" if track.counted else ""
        cv2.putText(frame, f"ID {track.id}{suffix}", (int(bx * width), max(20, int(by * height) - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        points = track.detection.keypoints
        valid = lambda key: key in points and points[key][2] >= c.pose_confidence
        pixel = lambda key: (int(points[key][0] * width), int(points[key][1] * height))
        if valid("neck") and valid("tail_root"):
            cv2.line(frame, pixel("neck"), pixel("tail_root"), color, 4)
            cv2.circle(frame, pixel("neck"), 5, color, -1)
            cv2.circle(frame, pixel("tail_root"), 5, color, -1)
        # El círculo se centra en el hocico inferido, no en una esquina de la caja.
        if valid("nose"):
            radius = max(8, min(35, int(bh * height * .12)))
            cv2.circle(frame, pixel("nose"), radius, color, 3)
        cv2.circle(frame, (int(track.detection.x * width), int(track.detection.y * height)), 4, color, -1)
    totals = counter.ledger.totals
    lines = ["  ".join(f"{k}: {v}" for k, v in totals.items()),
             "ESPACIO pausa | [ ] seleccion | A adulto | B becerro | P pendiente | Q salir"]
    if counter.ledger.count_only:
        lines = [f"Bovinos que cruzaron: {totals['total']}"]
    pose_tracks = [t for t in counter.tracks.values() if t.last_seen >= counter.timestamp - 1e-6 and t.detection.keypoints]
    if pose_tracks:
        lines.append(f"Bovinos detectados en ROI: {len(pose_tracks)} | circulo: hocico | linea: cuello-base de cola")
    if selected is not None and not counter.ledger.count_only:
        event = next(e for e in counter.ledger.events if e.id == selected)
        lines.append(f"Evento seleccionado: {event.id} ({event.category})")
    if warming:
        lines.append("Preparando fondo: mantener la manga VACIA")
    if paused:
        lines.append("EN PAUSA" if counter.ledger.count_only else "PAUSA / REVISION")
    cv2.rectangle(frame, (0, 0), (width, 24 * len(lines) + 7), (20, 20, 20), -1)
    for i, text in enumerate(lines):
        position = (10, 22 + 24 * i)
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return frame
