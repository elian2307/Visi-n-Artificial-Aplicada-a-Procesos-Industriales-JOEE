"""Demostracion local interactiva que reutiliza el detector y contador del prototipo."""
import argparse
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import time

import cv2
import numpy as np

from conteo_bovino.config import Config
from conteo_bovino.core import Counter, Ledger
from conteo_bovino.vision import create_detector, draw

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT / "assets/internet/mendeley-dk54zg67dd-v1/dataset/Videos/Toros7.mp4"))
    parser.add_argument("--config", default=str(ROOT / "config/internet-toros7.json"))
    parser.add_argument("--start-seconds", type=float, default=7.2)
    parser.add_argument("--end-seconds", type=float)
    parser.add_argument("--detector", choices=("motion", "pose"), default="motion")
    parser.add_argument("--frame-stride", type=int, default=1)
    parser.add_argument("--pose-model-dir", default=str(ROOT / "models/animal_pose"))
    args = parser.parse_args()
    count_only = args.detector == "pose"
    if not math.isfinite(args.start_seconds) or args.start_seconds < 0:
        raise ValueError("El inicio debe ser finito y no negativo.")
    if args.end_seconds is not None and (not math.isfinite(args.end_seconds) or args.end_seconds <= args.start_seconds):
        raise ValueError("El final debe ser finito y mayor que el inicio.")
    if args.frame_stride < 1:
        raise ValueError("El salto de fotogramas debe ser positivo.")
    config = Config.load(args.config)
    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        raise ValueError("No se pudo abrir el video de la demostracion.")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not math.isfinite(fps) or fps <= 0:
        fps = 30
    start_frame = int(np.ceil(args.start_seconds * fps))
    end_frame = int(np.ceil(args.end_seconds * fps)) if args.end_seconds is not None else int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    window = "Conteo bovino - Cabeza y lomo" if args.detector == "pose" else "Conteo bovino - Demostracion en vivo"
    counter = motion = metadata = output = None

    def save(status):
        if counter is not None:
            metadata["status"] = status
            counter.ledger.save(output, metadata)

    def reset():
        nonlocal counter, motion, metadata, output
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        ok, preview = cap.read()
        if not ok:
            raise ValueError("El intervalo de demostracion no tiene fotogramas.")
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        counter = Counter(config, Ledger(count_only=count_only))
        motion = create_detector(config, args.detector, args.pose_model_dir)
        output = ROOT / "runs/demostracion-en-vivo" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        metadata = dict(source=str(Path(args.source).resolve()), config=asdict(config), fps=fps,
                        start_frame=start_frame, end_frame=end_frame, detector=args.detector, frame_stride=args.frame_stride,
                        processed_frames=0, status="pausa_inicial", count_only=count_only,
                        started_at=datetime.now().astimezone().isoformat(), launcher="scripts.show_demo")
        save("pausa_inicial")
        return preview

    finished = False
    try:
        frame = reset()
        paused, finished, selected = True, False, None
        cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
        while True:
            tick = time.monotonic()
            if not paused:
                ok, next_frame = cap.read() if start_frame + metadata["processed_frames"] * args.frame_stride < end_frame else (False, None)
                if not ok:
                    paused, finished = True, True
                    save("fin_video")
                else:
                    frame = next_frame
                    timestamp = (start_frame + metadata["processed_frames"] * args.frame_stride) / fps
                    detections = motion.detect(frame, occupied=bool(counter.tracks))
                    events = counter.update(detections, timestamp)
                    metadata["processed_frames"] += 1
                    if events:
                        selected = selected or events[0].id
                        save("en_proceso")
                    for _ in range(args.frame_stride - 1):
                        if not cap.grab():
                            break
            annotated = draw(frame.copy(), counter, selected, args.detector == "motion" and motion.frames < config.warmup_frames, paused)
            canvas = np.zeros((frame.shape[0] + 82, frame.shape[1], 3), dtype=np.uint8)
            canvas[:frame.shape[0]] = annotated
            status = "FINALIZADO: revisa el total / R para repetir" if finished else ("LISTO / PAUSA: presiona ESPACIO" if paused else "PROCESANDO VIDEO ORIGINAL")
            cv2.putText(canvas, status, (12, frame.shape[0] + 25), cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 255, 255), 2)
            controls = ("ESPACIO iniciar/pausar | R repetir | Q salir" if count_only else
                        "ESPACIO iniciar/pausar | R repetir | [ ] evento | A/B/P corregir | Q salir")
            cv2.putText(canvas, controls,
                        (12, frame.shape[0] + 58), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
            cv2.imshow(window, canvas)
            delay = 20 if paused else max(1, int(1000 * args.frame_stride / fps - (time.monotonic() - tick) * 1000))
            key = cv2.waitKey(delay) & 0xFF
            if key in (27, ord("q")) or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == ord("r"):
                save("fin_video" if finished else "reiniciado_por_operador")
                frame = reset()
                paused, finished, selected = False, False, None
            elif key == ord(" ") and not finished:
                paused = not paused
            elif selected is not None and not count_only:
                if key in (ord("["), ord("]")):
                    selected = max(1, min(len(counter.ledger.events), selected + (-1 if key == ord("[") else 1)))
                category = {ord("a"): "adulto", ord("b"): "becerro", ord("p"): "pendiente"}.get(key)
                if category and counter.ledger.review(selected, category, "teclado_demo", time.time()):
                    save("fin_video" if finished else "en_revision")
    finally:
        if metadata is not None:
            metadata["ended_at"] = datetime.now().astimezone().isoformat()
            save("fin_video" if finished else "detenido_por_operador")
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
