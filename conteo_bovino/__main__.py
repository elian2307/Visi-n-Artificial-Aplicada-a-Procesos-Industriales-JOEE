import argparse
from dataclasses import asdict
from datetime import datetime
import json
import math
from pathlib import Path
import sys
import time

from .config import Config
from .core import Counter, GestureLatch, Ledger


def capture_source(value):
    return int(value) if str(value).isdigit() else str(value)


def calibrate(args):
    import cv2
    c = Config.load(args.config)
    cap = cv2.VideoCapture(capture_source(args.source))
    try:
        ok, frame = cap.read()
        if not ok:
            raise ValueError("No se pudo leer la fuente para calibrar.")
        height, width = frame.shape[:2]
        roi = cv2.selectROI("Selecciona la manga y presiona ENTER", frame, showCrosshair=True)
        cv2.destroyAllWindows()
        x, y, w, h = roi
        if not w or not h:
            raise ValueError("Calibracion cancelada.")
        c.roi = (x / width, y / height, w / width, h / height)
        clicks = []
        labels = ["Clic en linea A (entrada)", "Clic en linea B (salida)"]
        if args.reference_height_cm is not None:
            labels += ["Clic en el suelo de la referencia", "Clic en la cima de la referencia"]

        def click(event, px, py, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(clicks) < len(labels):
                clicks.append((px, py))

        window = "Calibracion - ESC cancela"
        cv2.namedWindow(window)
        cv2.setMouseCallback(window, click)
        while len(clicks) < len(labels):
            preview = frame.copy()
            cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 255), 2)
            cv2.putText(preview, labels[len(clicks)], (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            for px, py in clicks:
                cv2.circle(preview, (px, py), 5, (0, 255, 0), -1)
            cv2.imshow(window, preview)
            if cv2.waitKey(20) & 0xFF == 27 or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                raise ValueError("Calibracion cancelada.")
        c.line_a, c.line_b = clicks[0][0] / width, clicks[1][0] / width
        c.direction = "right" if c.line_b > c.line_a else "left"
        # Una geometría nueva invalida la calibración previa de altura.
        c.ground_y = c.reference_top_y = c.reference_height_cm = c.adult_threshold_cm = None
        if len(clicks) == 4:
            if args.adult_threshold_cm is None:
                raise ValueError("Para calibrar alturas especifica tambien --adult-threshold-cm.")
            c.ground_y = clicks[2][1] / height
            c.reference_top_y = clicks[3][1] / height
            c.reference_height_cm = args.reference_height_cm
            c.adult_threshold_cm = args.adult_threshold_cm
            c.uncertainty_cm = args.uncertainty_cm
        c.validate().save(args.save_config)
        print(f"Configuracion guardada: {Path(args.save_config).resolve()}")
    finally:
        cap.release()
        cv2.destroyAllWindows()


def review_saved(args):
    session = Path(args.review_session).resolve()
    ledger, metadata = Ledger.load(session)
    if args.event is None or args.category is None:
        raise ValueError("Usa --event ID --category adulto|becerro|pendiente.")
    ledger.review(args.event, args.category, "revision_terminal", time.time())
    ledger.save(session.parent, metadata)
    print(json.dumps(ledger.totals, ensure_ascii=False))


def run(args):
    import cv2
    from .vision import create_detector, draw

    c = Config.load(args.config)
    if args.max_frames is not None and args.max_frames <= 0:
        raise ValueError("--max-frames debe ser positivo.")
    source = capture_source(args.source)
    if args.smooth_output and (not args.output_video or isinstance(source, int)):
        raise ValueError("--smooth-output requiere un archivo de entrada y --output-video.")
    if args.frame_stride < 1 or (isinstance(source, int) and args.frame_stride != 1):
        raise ValueError("--frame-stride debe ser positivo y solo se puede usar con archivos.")
    if not math.isfinite(args.start_seconds) or args.start_seconds < 0:
        raise ValueError("--start-seconds debe ser finito y no negativo.")
    if args.end_seconds is not None and (not math.isfinite(args.end_seconds) or args.end_seconds <= args.start_seconds):
        raise ValueError("--end-seconds debe ser finito y mayor que --start-seconds.")
    if isinstance(source, int) and (args.start_seconds or args.end_seconds is not None):
        raise ValueError("Los intervalos solo se pueden seleccionar en archivos de video.")
    if isinstance(source, str) and not Path(source).is_file():
        raise ValueError(f"No existe el video: {source}")
    if args.no_display and args.gesture_camera is not None:
        raise ValueError("La revision por gestos requiere mostrar el evento seleccionado.")
    directory = Path(args.output or (Path("runs") / datetime.now().strftime("%Y%m%d-%H%M%S-%f"))).resolve()
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("La carpeta de resultados debe estar vacia para no sobrescribir otra sesion.")
    directory.mkdir(parents=True, exist_ok=True)
    count_only = args.detector == "pose"
    if count_only and args.gesture_camera is not None:
        raise ValueError("El modo pose cuenta bovinos sin revision de categorias.")
    ledger = Ledger(count_only=count_only)
    counter = Counter(c, ledger)
    motion = create_detector(c, args.detector, args.pose_model_dir)
    metadata = dict(source=str(source), started_at=datetime.now().astimezone().isoformat(), config=asdict(c),
                    opencv=cv2.__version__, processed_frames=0, status="iniciando", detector=args.detector,
                    frame_stride=args.frame_stride, count_only=count_only, smooth_output=args.smooth_output)
    if args.detector == "pose":
        manifest = Path(args.pose_model_dir) / "manifest.json"
        if manifest.is_file():
            metadata["models"] = json.loads(manifest.read_text(encoding="utf-8"))
    cap = operator = hands = writer = None
    selected = None
    latch = GestureLatch(c.gesture_hold_seconds, c.gesture_release_seconds)
    frame = None
    paused = False
    timestamp = 0.0
    start_clock = time.monotonic()
    pose_log = None
    try:
        if args.detector == "pose":
            pose_log = (directory / "detections.jsonl").open("w", encoding="utf-8")
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise ValueError("No se pudo abrir el video o la camara.")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            fps = 30.0
        metadata["fps"] = fps
        start_frame = math.ceil(args.start_seconds * fps)
        end_frame = math.ceil(args.end_seconds * fps) if args.end_seconds is not None else None
        if start_frame:
            if start_frame >= cap.get(cv2.CAP_PROP_FRAME_COUNT) or not cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame):
                raise ValueError("No se pudo acceder al inicio del intervalo.")
        metadata.update(start_frame=start_frame, start_seconds=start_frame / fps, requested_end_seconds=args.end_seconds)
        if args.gesture_camera is not None:
            if isinstance(source, int) and source == args.gesture_camera:
                raise ValueError("Usa camaras distintas para el corral y el operador.")
            from .gestures import Hands
            hands = Hands(args.hand_model)
            operator = cv2.VideoCapture(args.gesture_camera)
            if not operator.isOpened():
                raise ValueError("No se pudo abrir la camara del operador.")
        metadata["status"] = "en_proceso"
        ledger.save(directory, metadata)
        while True:
            loop_start = time.monotonic()
            if not paused:
                if end_frame is not None and start_frame + metadata["processed_frames"] * args.frame_stride >= end_frame:
                    metadata["status"] = "fin_intervalo"
                    break
                ok, frame = cap.read()
                if not ok:
                    if metadata["processed_frames"] == 0:
                        raise ValueError("La fuente se abrio pero no entrego fotogramas.")
                    metadata["status"] = "fin_video" if isinstance(source, str) else "captura_interrumpida"
                    break
                index = metadata["processed_frames"]
                timestamp = (start_frame + index * args.frame_stride) / fps if isinstance(source, str) else time.monotonic() - start_clock
                detections = motion.detect(frame, occupied=bool(counter.tracks))
                created = counter.update(detections, timestamp)
                if pose_log is not None:
                    pose_log.write(json.dumps(dict(timestamp_seconds=timestamp,
                        detections=[asdict(d) for d in detections],
                        tracks=[dict(id=t.id, counted=t.counted, x=t.detection.x, y=t.detection.y)
                                for t in counter.tracks.values() if t.last_seen == timestamp])) + "\n")
                metadata["processed_frames"] += 1
                if created:
                    # Mantener una selección explícita: nuevos cruces no cambian el objetivo del gesto.
                    if selected is None:
                        selected = created[0].id
                    ledger.save(directory, metadata)
                warming = args.detector == "motion" and motion.frames <= c.warmup_frames
                if args.output_video:
                    if writer is None:
                        output_fps = fps if args.smooth_output else fps / args.frame_stride
                        writer = cv2.VideoWriter(str(directory / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), output_fps,
                                                 (frame.shape[1], frame.shape[0]))
                        if not writer.isOpened():
                            raise ValueError("No se pudo crear el video anotado.")
                    writer.write(draw(frame.copy(), counter, selected, warming))
                for offset in range(1, args.frame_stride):
                    if args.smooth_output:
                        source_index = start_frame + index * args.frame_stride + offset
                        if end_frame is not None and source_index >= end_frame:
                            break
                        ok, intermediate = cap.read()
                        if not ok:
                            break
                        writer.write(draw(intermediate, counter, selected, warming))
                    elif not cap.grab():
                        break
            if hands is not None:
                ok, operator_frame = operator.read()
                if not ok:
                    raise ValueError("Se interrumpio la camara del operador.")
                now = time.monotonic()
                gesture = hands.detect(operator_frame, int((now - start_clock) * 1000))
                command = latch.update(gesture, selected, now)
                if command is not None and selected is not None:
                    if ledger.review(selected, command, "gesto", time.time()):
                        ledger.save(directory, metadata)
                label = f"Gesto: {gesture or '-'} | objetivo: {selected or '-'}"
                cv2.putText(operator_frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Operador - 1 adulto / 2 becerro / palma pendiente", operator_frame)
            if not args.no_display:
                cv2.imshow("Conteo bovino", draw(frame.copy(), counter, selected, args.detector == "motion" and motion.frames <= c.warmup_frames, paused))
                delay = 20 if paused or isinstance(source, int) else max(1, int(1000 * args.frame_stride / fps - (time.monotonic() - loop_start) * 1000))
                key = cv2.waitKey(delay) & 0xFF
                if key in (ord("q"), 27) or cv2.getWindowProperty("Conteo bovino", cv2.WND_PROP_VISIBLE) < 1:
                    metadata["status"] = "detenido_por_operador"
                    break
                if key == ord(" "):
                    if isinstance(source, int):
                        print("La captura en vivo no se pausa; selecciona y revisa mientras continua.")
                    else:
                        paused = not paused
                if ledger.events and key in (ord("["), ord("]")):
                    ids = [e.id for e in ledger.events]
                    index = ids.index(selected) if selected in ids else 0
                    selected = ids[max(0, min(len(ids) - 1, index + (-1 if key == ord("[") else 1)))]
                category = {ord("a"): "adulto", ord("b"): "becerro", ord("p"): "pendiente"}.get(key)
                if not count_only and category is not None and selected is not None:
                    if ledger.review(selected, category, "teclado", time.time()):
                        ledger.save(directory, metadata)
            if args.max_frames is not None and metadata["processed_frames"] >= args.max_frames:
                metadata["status"] = "limite_fotogramas"
                break
        print(json.dumps(ledger.totals, ensure_ascii=False))
        print(f"Resultados: {directory}")
    except KeyboardInterrupt:
        metadata["status"] = "interrumpido_por_operador"
        print(f"Interrumpido. Resultados: {directory}")
    except Exception as error:
        metadata.update(status="error", error=str(error))
        raise
    finally:
        metadata["ended_at"] = datetime.now().astimezone().isoformat()
        metadata["elapsed_seconds"] = time.monotonic() - start_clock
        ledger.save(directory, metadata)
        if pose_log is not None:
            pose_log.close()
        for resource in (writer, hands, operator, cap):
            if resource is not None:
                resource.close() if resource is hands else resource.release()
        if not args.no_display:
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Conteo de bovinos por cruces A -> B. Inicializa con la manga vacia.")
    parser.add_argument("--source", default="0", help="Ruta de video o indice de camara (0).")
    parser.add_argument("--config", help="JSON de geometria y calibracion.")
    parser.add_argument("--output", help="Carpeta vacia para resultados; por defecto runs/fecha.")
    parser.add_argument("--no-display", action="store_true", help="Procesar sin ventanas ni revision en vivo.")
    parser.add_argument("--output-video", action="store_true", help="Guardar annotated.mp4 junto a CSV y JSON.")
    parser.add_argument("--smooth-output", action="store_true", help="Conservar todos los fotogramas originales en el video anotado.")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--detector", choices=("motion", "pose"), default="motion")
    parser.add_argument("--pose-model-dir", default="models/animal_pose")
    parser.add_argument("--frame-stride", type=int, default=1, help="Inferir uno de cada N fotogramas de un archivo, conservando su tiempo.")
    parser.add_argument("--start-seconds", type=float, default=0, help="Comenzar en este segundo de un archivo, sin recodificarlo.")
    parser.add_argument("--end-seconds", type=float, help="Terminar antes de este segundo; los eventos conservan el tiempo original.")
    parser.add_argument("--gesture-camera", type=int, help="Camara independiente del operador, p. ej. 1.")
    parser.add_argument("--hand-model", default="models/hand_landmarker.task")
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--save-config", default="config/local.json")
    parser.add_argument("--reference-height-cm", type=float)
    parser.add_argument("--adult-threshold-cm", type=float)
    parser.add_argument("--uncertainty-cm", type=float, default=10)
    parser.add_argument("--review-session", help="session.json previo para corregir un evento sin volver a contar.")
    parser.add_argument("--event", type=int)
    parser.add_argument("--category", choices=("adulto", "becerro", "pendiente"))
    args = parser.parse_args()
    try:
        if args.review_session:
            review_saved(args)
        elif args.calibrate:
            calibrate(args)
        else:
            run(args)
    except (ValueError, OSError, TypeError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
