from __future__ import annotations

import csv
import time
from pathlib import Path

import cv2
import typer

from .config import AppConfig, CameraConfig, create_default_config, load_config, save_config
from .speed import SpeedEstimator
from .tracker import CentroidTracker, Track
from .yolo_onnx import YoloOnnxDetector


app = typer.Typer(add_completion=False, help="CLI deteksi kendaraan dan estimasi kecepatan.")

CAMERA_BACKENDS = {
    "auto": None,
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
    "v4l2": cv2.CAP_V4L2,
    "ffmpeg": cv2.CAP_FFMPEG,
    "gstreamer": cv2.CAP_GSTREAMER,
    "any": cv2.CAP_ANY,
}


def _resolve_source(source: str | int) -> str | int:
    if isinstance(source, int):
        return source
    return int(source) if source.isdigit() else source


def _is_camera_source(source: str | int) -> bool:
    return isinstance(source, int) or (isinstance(source, str) and source.isdigit())


def _ensure_parent(path: str | None) -> None:
    if not path:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _draw_line(frame, start, end, color, text) -> None:
    cv2.line(frame, start, end, color, 2)
    text_x = min(start[0], end[0]) + 8
    text_y = min(start[1], end[1]) - 8
    cv2.putText(frame, text, (text_x, max(20, text_y)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def _draw_track(frame, track: Track, speed_text: str | None) -> None:
    x1, y1, x2, y2 = track.box
    cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 220, 40), 2)

    title = f"ID {track.track_id} | {track.label} | {track.confidence:.2f}"
    if speed_text:
        title = f"{title} | {speed_text}"
    cv2.putText(
        frame,
        title,
        (x1, max(25, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )

    centers = list(track.trail)
    for index in range(1, len(centers)):
        cv2.line(frame, centers[index - 1], centers[index], (255, 120, 0), 2)


def _open_capture(source: str | int, camera_cfg: CameraConfig) -> tuple[cv2.VideoCapture, bool]:
    resolved_source = _resolve_source(source)
    is_camera = _is_camera_source(resolved_source)

    if is_camera:
        backend = CAMERA_BACKENDS.get(camera_cfg.backend.lower())
        if camera_cfg.backend.lower() not in CAMERA_BACKENDS:
            raise typer.BadParameter(f"Backend kamera tidak dikenal: {camera_cfg.backend}")

        capture = None
        for _ in range(max(1, camera_cfg.retry_open_count)):
            if backend is None:
                capture = cv2.VideoCapture(int(resolved_source))
            else:
                capture = cv2.VideoCapture(int(resolved_source), backend)

            if capture.isOpened():
                break
            capture.release()
            capture = None
            time.sleep(0.25)

        if capture is None or not capture.isOpened():
            raise typer.BadParameter(f"Tidak bisa membuka kamera device: {source}")

        if camera_cfg.width > 0:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, camera_cfg.width)
        if camera_cfg.height > 0:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_cfg.height)
        if camera_cfg.fps > 0:
            capture.set(cv2.CAP_PROP_FPS, camera_cfg.fps)

        for _ in range(max(0, camera_cfg.warmup_frames)):
            ok, _ = capture.read()
            if not ok:
                break

        return capture, True

    capture = cv2.VideoCapture(str(resolved_source))
    if not capture.isOpened():
        raise typer.BadParameter(f"Tidak bisa membuka sumber video: {source}")
    return capture, False


def _apply_camera_transforms(frame, camera_cfg: CameraConfig):
    if camera_cfg.flip_horizontal:
        frame = cv2.flip(frame, 1)
    if camera_cfg.flip_vertical:
        frame = cv2.flip(frame, 0)
    return frame


def _is_model_ready(model_path: str) -> bool:
    return Path(model_path).exists()


def _format_status(ok: bool) -> str:
    return "OK" if ok else "FAIL"


@app.command()
def run(
    config: str = typer.Option("configs/default.yaml", "--config", "-c", help="Path file YAML konfigurasi."),
) -> None:
    """Proses video dan hitung kecepatan kendaraan."""
    cfg = load_config(config)
    _run_pipeline(cfg)


@app.command()
def cameras(
    max_devices: int = typer.Option(5, "--max-devices", min=1, max=20, help="Jumlah index kamera yang discan."),
    backend: str = typer.Option("auto", "--backend", help="Backend kamera OpenCV."),
) -> None:
    """Scan kamera device yang tersedia."""
    backend_name = backend.lower()
    if backend_name not in CAMERA_BACKENDS:
        raise typer.BadParameter(f"Backend kamera tidak dikenal: {backend}")

    backend_id = CAMERA_BACKENDS[backend_name]
    found = 0
    for device_index in range(max_devices):
        if backend_id is None:
            capture = cv2.VideoCapture(device_index)
        else:
            capture = cv2.VideoCapture(device_index, backend_id)

        ok, frame = capture.read()
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        if ok and frame is not None:
            typer.echo(f"[OK] device={device_index} backend={backend_name} size={width}x{height} fps={fps:.1f}")
            found += 1
        else:
            typer.echo(f"[--] device={device_index} backend={backend_name} tidak tersedia")
        capture.release()

    if found == 0:
        raise typer.Exit(code=1)


@app.command("init-config")
def init_config(
    output: str = typer.Option("configs/local.yaml", "--output", "-o", help="Path file konfigurasi hasil generate."),
    preset: str = typer.Option("camera", "--preset", help="Preset: camera, video, termux."),
    source: str = typer.Option("", "--source", help="Override source, misalnya 0 atau path video."),
    model_path: str = typer.Option("models/yolov8n.onnx", "--model-path", help="Path model ONNX."),
) -> None:
    """Generate file konfigurasi siap pakai."""
    config = create_default_config(preset)
    if source:
        config.source = int(source) if source.isdigit() else source
    if model_path:
        config.model.path = model_path

    written = save_config(config, output)
    typer.echo(f"Konfigurasi berhasil dibuat: {written}")
    typer.echo(f"Preset: {preset}")
    typer.echo(f"Source: {config.source}")
    typer.echo(f"Model: {config.model.path}")


@app.command()
def doctor(
    config: str = typer.Option("configs/camera.yaml", "--config", "-c", help="Path file YAML konfigurasi."),
    check_camera: bool = typer.Option(False, "--check-camera", help="Coba buka camera source dari config."),
) -> None:
    """Periksa apakah environment dan konfigurasi siap dipakai."""
    results: list[tuple[str, bool, str]] = []
    config_path = Path(config)
    results.append(("config_file", config_path.exists(), str(config_path)))

    if not config_path.exists():
        for name, ok, detail in results:
            typer.echo(f"[{_format_status(ok)}] {name}: {detail}")
        raise typer.Exit(code=1)

    try:
        cfg = load_config(config_path)
        results.append(("config_load", True, f"source={cfg.source}"))
    except Exception as exc:
        results.append(("config_load", False, str(exc)))
        for name, ok, detail in results:
            typer.echo(f"[{_format_status(ok)}] {name}: {detail}")
        raise typer.Exit(code=1)

    results.append(("opencv", hasattr(cv2, "VideoCapture"), f"version={cv2.__version__}"))
    results.append(("model_file", _is_model_ready(cfg.model.path), cfg.model.path))

    if check_camera and _is_camera_source(cfg.source):
        try:
            capture, _ = _open_capture(cfg.source, cfg.camera)
            ok, frame = capture.read()
            results.append(("camera_open", bool(ok and frame is not None), f"device={cfg.source}"))
            capture.release()
        except Exception as exc:
            results.append(("camera_open", False, str(exc)))

    has_failure = False
    for name, ok, detail in results:
        typer.echo(f"[{_format_status(ok)}] {name}: {detail}")
        has_failure = has_failure or not ok

    if has_failure:
        raise typer.Exit(code=1)


def _run_pipeline(cfg: AppConfig) -> None:
    detector = YoloOnnxDetector(
        model_path=cfg.model.path,
        input_size=cfg.model.input_size,
        score_threshold=cfg.model.score_threshold,
        confidence_threshold=cfg.model.confidence_threshold,
        nms_threshold=cfg.model.nms_threshold,
        labels=cfg.model.labels,
        allowed_classes=cfg.model.allowed_classes,
    )
    tracker = CentroidTracker(
        max_distance=cfg.tracking.max_distance,
        max_missing_frames=cfg.tracking.max_missing_frames,
        min_confirmed_hits=cfg.tracking.min_confirmed_hits,
        trail_size=cfg.tracking.trail_size,
    )
    estimator = SpeedEstimator(
        line_a_start=cfg.speed.line_a.start,
        line_a_end=cfg.speed.line_a.end,
        line_b_start=cfg.speed.line_b.start,
        line_b_end=cfg.speed.line_b.end,
        real_distance_meters=cfg.speed.real_distance_meters,
        min_speed_kmh=cfg.speed.min_speed_kmh,
        max_speed_kmh=cfg.speed.max_speed_kmh,
    )

    capture, is_camera = _open_capture(cfg.source, cfg.camera)

    fps = capture.get(cv2.CAP_PROP_FPS) or cfg.camera.fps or 30.0
    if fps <= 1.0:
        fps = cfg.camera.fps or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    live_started_at = time.perf_counter()

    writer = None
    if cfg.output_video:
        _ensure_parent(cfg.output_video)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(cfg.output_video, fourcc, fps, (width, height))

    event_file = None
    event_writer = None
    if cfg.output_events_csv:
        _ensure_parent(cfg.output_events_csv)
        event_file = open(cfg.output_events_csv, "w", newline="", encoding="utf-8")
        event_writer = csv.writer(event_file)
        event_writer.writerow(["track_id", "label", "direction", "speed_kmh", "elapsed_seconds", "frame"])

    frame_index = 0
    processed_frames = 0
    recorded_events = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if is_camera:
                frame = _apply_camera_transforms(frame, cfg.camera)

            frame_index += 1
            if cfg.skip_frames and (frame_index - 1) % (cfg.skip_frames + 1) != 0:
                continue

            detections = detector.predict(frame)
            active_tracks = tracker.update(detections)
            if is_camera:
                timestamp_sec = time.perf_counter() - live_started_at
            else:
                timestamp_sec = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if timestamp_sec <= 0:
                timestamp_sec = processed_frames / fps

            _draw_line(
                frame,
                cfg.speed.line_a.start,
                cfg.speed.line_a.end,
                cfg.speed.line_a.color_bgr,
                f"{cfg.speed.line_a.name} ({cfg.speed.real_distance_meters:.1f} m total)",
            )
            _draw_line(
                frame,
                cfg.speed.line_b.start,
                cfg.speed.line_b.end,
                cfg.speed.line_b.color_bgr,
                cfg.speed.line_b.name,
            )

            for track in active_tracks:
                event = estimator.update(
                    track_id=track.track_id,
                    label=track.label,
                    previous_center=track.previous_center,
                    current_center=track.center,
                    timestamp_sec=timestamp_sec,
                    frame_index=frame_index,
                )
                state = estimator.get_state(track.track_id)
                speed_text = f"{state.speed_kmh:.1f} km/h" if state.speed_kmh is not None else None
                _draw_track(frame, track, speed_text)

                if event_writer and event is not None:
                    event_writer.writerow(
                        [
                            event.track_id,
                            event.label,
                            event.direction,
                            f"{event.speed_kmh:.2f}",
                            f"{event.elapsed_seconds:.3f}",
                            event.frame_index,
                        ]
                    )
                    recorded_events += 1

            processed_frames += 1
            cv2.putText(
                frame,
                f"Frame: {processed_frames} | Kendaraan aktif: {len(active_tracks)} | Event: {recorded_events}",
                (16, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"Sumber: {'camera' if is_camera else 'video'} | {width}x{height} @ {fps:.1f} FPS",
                (16, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            if writer is not None:
                writer.write(frame)

            if cfg.display:
                cv2.imshow("cardetec", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if cfg.max_frames is not None and processed_frames >= cfg.max_frames:
                break
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if event_file is not None:
            event_file.close()
        if cfg.display:
            cv2.destroyAllWindows()

    typer.echo(f"Selesai. Frame diproses: {processed_frames}. Event kecepatan: {recorded_events}.")
    if cfg.output_video:
        typer.echo(f"Video keluaran: {cfg.output_video}")
    if cfg.output_events_csv:
        typer.echo(f"CSV event: {cfg.output_events_csv}")


if __name__ == "__main__":
    app()
