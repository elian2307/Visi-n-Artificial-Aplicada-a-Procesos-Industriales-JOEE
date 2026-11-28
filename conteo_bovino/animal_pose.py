"""Detección individual COCO (vaca) + puntos anatómicos AP-10K con OpenCV DNN."""
from pathlib import Path

import cv2
import numpy as np

from .core import Detection

KEYPOINT_NAMES = ("left_eye", "right_eye", "nose", "neck", "tail_root", "left_shoulder", "left_elbow",
                  "left_front_paw", "right_shoulder", "right_elbow", "right_front_paw", "left_hip",
                  "left_knee", "left_back_paw", "right_hip", "right_knee", "right_back_paw")


def box_iou(a, b):
    x, y, w, h = a
    ox, oy, ow, oh = b
    intersection = max(0, min(x + w, ox + ow) - max(x, ox)) * max(0, min(y + h, oy + oh) - max(y, oy))
    union = w * h + ow * oh - intersection
    return intersection / union if union > 0 else 0


def suppress_shared_heads(detections, threshold=.3):
    """Suprime cajas duplicadas que predicen el mismo hocico y cuello; conserva cabezas distintas."""
    def quality(d):
        scores = [min(1, d.keypoints[k][2]) for k in ("nose", "neck", "tail_root")]
        return (sum(scores) / 3 + (d.confidence or 0)) / 2

    kept = []
    for d in sorted(detections, key=quality, reverse=True):
        duplicate = False
        for other in kept:
            if min(d.keypoints["nose"][2], other.keypoints["nose"][2]) < threshold:
                continue
            if min(d.keypoints["neck"][2], other.keypoints["neck"][2]) < min(.2, threshold):
                continue
            x, y, w, h = d.box
            ox, oy, ow, oh = other.box
            intersection = max(0, min(x+w, ox+ow)-max(x, ox)) * max(0, min(y+h, oy+oh)-max(y, oy))
            union = w*h + ow*oh - intersection
            size = min(np.hypot(w, h), np.hypot(ow, oh))
            head_distance = np.hypot(d.keypoints["nose"][0]-other.keypoints["nose"][0], d.keypoints["nose"][1]-other.keypoints["nose"][1])
            neck_distance = np.hypot(d.keypoints["neck"][0]-other.keypoints["neck"][0], d.keypoints["neck"][1]-other.keypoints["neck"][1])
            if union > 0 and intersection / union > .15 and head_distance < .08 * size and neck_distance < .12 * size:
                duplicate = True
                break
        if not duplicate:
            kept.append(d)
    return kept


def decode_simcc(simcc_x, simcc_y, inverse_affine):
    """Devuelve coordenadas de la imagen original y puntuación mínima X/Y."""
    sx, sy = simcc_x.reshape(17, -1), simcc_y.reshape(17, -1)
    x, y = sx.argmax(axis=1).astype(np.float32) / 2, sy.argmax(axis=1).astype(np.float32) / 2
    scores = np.minimum(sx.max(axis=1), sy.max(axis=1))
    coordinates = np.stack([x, y, np.ones_like(x)], axis=-1) @ inverse_affine.T
    return coordinates, scores


class CattlePoseDetector:
    def __init__(self, config, model_dir="models/animal_pose"):
        self.config = config
        model_dir = Path(model_dir)
        detector_path, pose_path = model_dir / "yolox_s.onnx", model_dir / "rtmpose_ap10k.onnx"
        if not detector_path.is_file() or not pose_path.is_file():
            raise ValueError("Faltan los modelos animales. Ejecuta python -m scripts.download_pose_models.")
        self.detector = cv2.dnn.readNet(str(detector_path))
        self.pose = cv2.dnn.readNet(str(pose_path))
        for net in (self.detector, self.pose):
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            # CPU es el destino por defecto; no requiere CUDA ni una versión distinta de Python.
        grids, strides = [], []
        for stride in (8, 16, 32):
            yy, xx = np.meshgrid(np.arange(640 // stride), np.arange(640 // stride), indexing="ij")
            grids.append(np.stack([xx, yy], axis=-1).reshape(-1, 2))
            strides.append(np.full((xx.size, 1), stride))
        self.grids, self.strides = np.concatenate(grids), np.concatenate(strides)
        self.frames = 0
        self.mask = None

    def _boxes(self, bgr, threshold):
        height, width = bgr.shape[:2]
        ratio = min(640 / width, 640 / height)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (max(1, int(width * ratio)), max(1, int(height * ratio))))
        padded = np.full((640, 640, 3), 114, dtype=np.float32)
        padded[:resized.shape[0], :resized.shape[1]] = resized
        self.detector.setInput(np.ascontiguousarray(padded.transpose(2, 0, 1)[None]))
        predictions = self.detector.forward()[0]
        scores_all = predictions[:, 4:5] * predictions[:, 5:]
        # COCO clase 19: cow. No se incluyen caballos, personas u ovejas.
        keep = (scores_all.argmax(axis=1) == 19) & (scores_all[:, 19] >= threshold)
        if not keep.any():
            return []
        pred = predictions[keep]
        centers = (pred[:, :2] + self.grids[keep]) * self.strides[keep]
        sizes = np.exp(np.clip(pred[:, 2:4], -20, 20)) * self.strides[keep]
        boxes = np.concatenate([(centers - sizes / 2) / ratio, sizes / ratio], axis=1)
        scores = scores_all[keep, 19]
        indices = cv2.dnn.NMSBoxes(boxes.tolist(), scores.tolist(), threshold, 0.5)
        return [(boxes[int(i)], float(scores[int(i)])) for i in np.asarray(indices).reshape(-1)]

    def _candidates(self, frame):
        c = self.config
        full = self._boxes(frame, c.detector_confidence)
        if not c.pose_detail_pass:
            return [(box, score, False) for box, score in full]

        # Ampliar la zona de paso con margen para no cortar los animales al entrar.
        height, width = frame.shape[:2]
        x, y, w, h = c.roi
        left, top = max(0, int((x - .13) * width)), max(0, int((y - .10) * height))
        right = min(width, int((x + w + .08) * width))
        bottom = min(height, int((y + h + .08) * height))
        # En tomas de corral, quitar cielo y suelo deja más resolución para el ganado.
        if bottom - top < 8 or right - left < 8 or (left, top, right, bottom) == (0, 0, width, height):
            return [(box, score, False) for box, score in full]
        threshold = min(c.detector_confidence, .20)
        detail = self._boxes(frame[top:bottom, left:right], threshold)
        boxes = [(box, score, False) for box, score in full]
        offset = np.array([left, top, 0, 0])
        for box, score in detail:
            box = box + offset
            if all(box_iou(box, existing) < .62 for existing, _, _ in boxes):
                boxes.append((box, score, True))
        return boxes

    def _keypoints(self, bgr, box):
        x, y, w, h = box
        center = np.array([x + w / 2, y + h / 2], dtype=np.float32)
        size = max(w, h) * 1.25
        scale = 256 / max(size, 1)
        affine = np.array([[scale, 0, 128 - center[0] * scale],
                           [0, scale, 128 - center[1] * scale]], dtype=np.float32)
        crop = cv2.warpAffine(bgr, affine, (256, 256), flags=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32)
        rgb = (rgb - np.array([123.675, 116.28, 103.53], np.float32)) / np.array([58.395, 57.12, 57.375], np.float32)
        self.pose.setInput(np.ascontiguousarray(rgb.transpose(2, 0, 1)[None]))
        outputs = self.pose.forward(["simcc_x", "simcc_y"])
        return decode_simcc(outputs[0], outputs[1], cv2.invertAffineTransform(affine))

    def detect(self, frame, occupied=False):
        c = self.config
        height, width = frame.shape[:2]
        # Detectar la imagen completa conserva contexto; la ROI filtra el centro del cuerpo.
        detections = []
        for box, confidence, from_detail in self._candidates(frame):
            bx, by, bw, bh = box
            center_x, center_y = (bx + bw / 2) / width, (by + bh / 2) / height
            rx, ry, rw, rh = c.roi
            if not (rx <= center_x <= rx + rw and ry <= center_y <= ry + rh):
                continue
            coordinates, scores = self._keypoints(frame, box)
            keypoints = {}
            for name, point, score in zip(KEYPOINT_NAMES, coordinates, scores):
                px, py = float(point[0] / width), float(point[1] / height)
                # No mostrar como válidos puntos fuera de imagen o de la caja ampliada.
                valid = (0 <= px <= 1 and 0 <= py <= 1 and bx - bw * .25 <= point[0] <= bx + bw * 1.25
                         and by - bh * .25 <= point[1] <= by + bh * 1.25)
                keypoints[name] = (px, py, float(score) if valid else 0.0)
            if from_detail:
                nose, neck, tail = (keypoints[key][2] for key in ("nose", "neck", "tail_root"))
                if min(nose, neck, tail) < c.pose_confidence:
                    continue
            # El centro de la caja es la referencia de cruce. Los huesos estimados
            # distinguen/asocian individuos, pero su jitter no debe mover esa referencia.
            # La altura AP-10K no es una medición calibrada del borde del lomo.
            detections.append(Detection(center_x, center_y, (float(bx / width), float(by / height),
                                                           float(bw / width), float(bh / height)),
                                        keypoints=keypoints, confidence=confidence))
        self.frames += 1
        return suppress_shared_heads(detections, c.pose_confidence)
