from __future__ import annotations

import csv
import json
import os
import signal
import time
from pathlib import Path
import urllib.request

import cv2
import typer

from .config import AppConfig, CameraConfig, create_default_config, load_config, save_config
from .speed import SpeedEstimator
from .tracker import CentroidTracker, Track
from .yolo_onnx import YoloOnnxDetector


app = typer.Typer(add_completion=False, help="CLI deteksi kendaraan dan estimasi kecepatan.")
_STOP_REQUESTED = False

CAMERA_BACKENDS = {
    "auto": None,
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
    "v4l2": cv2.CAP_V4L2,
    "ffmpeg": cv2.CAP_FFMPEG,
    "gstreamer": cv2.CAP_GSTREAMER,
    "any": cv2.CAP_ANY,
}


# #region debug-point shared:cli-debug
def _debug_report(hypothesis_id: str, location: str, msg: str, data: dict | None = None, run_id: str = "pre-fix") -> None:
    data = data or {}
    url = "http://127.0.0.1:7777/event"
    session_id = os.getenv("CARDETEC_DEBUG_SESSION_ID", "camera-speed-realtime")
    env_path = os.getenv("CARDETEC_DEBUG_ENV_PATH", f".dbg/{session_id}.env")
    try:
        with open(env_path, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if line.startswith("DEBUG_SERVER_URL="):
                    url = line.split("=", 1)[1]
                elif line.startswith("DEBUG_SESSION_ID="):
                    session_id = line.split("=", 1)[1]
    except OSError:
        pass
    payload = {
        "sessionId": session_id,
        "runId": os.getenv("CARDETEC_DEBUG_RUN_ID", run_id),
        "hypothesisId": hypothesis_id,
        "location": location,
        "msg": f"[DEBUG] {msg}",
        "data": data,
    }
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=0.25,
        ).read()
    except Exception:
        pass


# #endregion


def _resolve_source(source: str | int) -> str | int:
    if isinstance(source, int):
        return source
    return int(source) if source.isdigit() else source


def _request_stop(signum, _frame) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    signal_name = getattr(signal.Signals(signum), "name", str(signum))
    # #region debug-point B:signal-stop-request
    _debug_report(
        "B",
        "cli.py:_request_stop",
        "Permintaan stop diterima dari signal OS",
        {"signal": signal_name, "signal_number": signum},
    )
    # #endregion


def _install_signal_handlers() -> dict[int, object]:
    previous_handlers: dict[int, object] = {}
    for sig_name in ("SIGINT", "SIGBREAK", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        previous_handlers[sig] = signal.getsignal(sig)
        signal.signal(sig, _request_stop)
    return previous_handlers


def _restore_signal_handlers(previous_handlers: dict[int, object]) -> None:
    for sig, handler in previous_handlers.items():
        signal.signal(sig, handler)


def _is_camera_source(source: str | int) -> bool:
    return isinstance(source, int) or (isinstance(source, str) and source.isdigit())


def _ensure_parent(path: str | None) -> None:
    if not path:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
def _format_speed_text(speed_kmh: float | None) -> str | None:
    if speed_kmh is None:
        return None
    return f"KEC: {speed_kmh:.1f} km/jam"


def _draw_track(frame, track: Track, speed_kmh: float | None, direction: str | None) -> None:
    x1, y1, x2, y2 = track.box
    box_color = (0, 255, 0) if speed_kmh is not None else (0, 215, 255)
    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

    title_line = f"ID:{track.track_id} {track.label.upper()}"
    speed_line = _format_speed_text(speed_kmh)
    if speed_line and direction:
        speed_line = f"{speed_line}  {direction}"

    if speed_line:
        (speed_width, speed_height), speed_baseline = cv2.getTextSize(speed_line, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)
        (title_width, title_height), title_baseline = cv2.getTextSize(title_line, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    else:
        (title_width, title_height), title_baseline = cv2.getTextSize(title_line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        speed_width = 0
        speed_height = 0
        speed_baseline = 0
    text_width = max(title_width, speed_width)
    text_height = title_height + title_baseline + 10
    if speed_line:
        text_height += speed_height + speed_baseline + 4
    text_top = max(0, y1 - text_height - 10)
    text_bottom = text_top + text_height
    text_right = min(frame.shape[1] - 1, x1 + text_width + 14)
    cv2.rectangle(frame, (x1, text_top), (text_right, text_bottom), box_color, -1)
    cv2.rectangle(frame, (x1, text_top), (text_right, text_bottom), (20, 20, 20), 1)
    if speed_line:
        cv2.putText(
            frame,
            speed_line,
            (x1 + 6, text_top + speed_height + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (0, 0, 0),
            2,
        )
        cv2.putText(
            frame,
            title_line,
            (x1 + 6, text_bottom - title_baseline - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (0, 0, 0),
            1,
        )
    else:
        cv2.putText(
            frame,
            title_line,
            (x1 + 6, text_top + title_height + 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
        )

    centers = list(track.trail)
    for index in range(1, len(centers)):
        cv2.line(frame, centers[index - 1], centers[index], (0, 180, 0), 1)


def _open_capture(source: str | int, camera_cfg: CameraConfig) -> tuple[cv2.VideoCapture, bool]:
    resolved_source = _resolve_source(source)
    is_camera = _is_camera_source(resolved_source)

    if is_camera:
        backend = CAMERA_BACKENDS.get(camera_cfg.backend.lower())
        if camera_cfg.backend.lower() not in CAMERA_BACKENDS:
            raise typer.BadParameter(f"Backend kamera tidak dikenal: {camera_cfg.backend}")

        capture = None
        try:
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

            # Use a shallow camera buffer so the pipeline keeps pulling the latest frame.
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if camera_cfg.backend.lower() in {"auto", "dshow", "msmf", "any"}:
                capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            if camera_cfg.width > 0:
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, camera_cfg.width)
            if camera_cfg.height > 0:
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_cfg.height)
            if camera_cfg.fps > 0:
                capture.set(cv2.CAP_PROP_FPS, camera_cfg.fps)

            for warmup_index in range(max(0, camera_cfg.warmup_frames)):
                if _STOP_REQUESTED:
                    raise KeyboardInterrupt()
                ok, _ = capture.read()
                if not ok:
                    break
                if warmup_index == 0:
                    # #region debug-point A:ctrlc-warmup-started
                    _debug_report(
                        "A",
                        "cli.py:_open_capture",
                        "Warmup frame kamera dimulai",
                        {"source": source, "warmup_frames": camera_cfg.warmup_frames},
                    )
                    # #endregion

            return capture, True
        except KeyboardInterrupt:
            # #region debug-point B:ctrlc-open-capture-interrupt
            _debug_report(
                "B",
                "cli.py:_open_capture",
                "KeyboardInterrupt terjadi saat membuka atau warmup kamera",
                {"source": source, "warmup_frames": camera_cfg.warmup_frames},
            )
            # #endregion
            if capture is not None:
                capture.release()
                # #region debug-point E:ctrlc-open-capture-released
                _debug_report(
                    "E",
                    "cli.py:_open_capture",
                    "capture.release dijalankan saat interrupt di fase open/warmup",
                    {"source": source},
                )
                # #endregion
            raise

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
    global _STOP_REQUESTED
    _STOP_REQUESTED = False
    previous_handlers = _install_signal_handlers()
    cfg = load_config(config)
    try:
        _run_pipeline(cfg)
    finally:
        _restore_signal_handlers(previous_handlers)


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
    global _STOP_REQUESTED
    # #region debug-point D:cli-detector-init-start
    _debug_report(
        "D",
        "cli.py:_run_pipeline",
        "Mulai inisialisasi detector YOLO",
        {"model_path": cfg.model.path, "input_size": cfg.model.input_size},
    )
    # #endregion
    detector = YoloOnnxDetector(
        model_path=cfg.model.path,
        input_size=cfg.model.input_size,
        score_threshold=cfg.model.score_threshold,
        confidence_threshold=cfg.model.confidence_threshold,
        nms_threshold=cfg.model.nms_threshold,
        labels=cfg.model.labels,
        allowed_classes=cfg.model.allowed_classes,
    )
    # #region debug-point D:cli-detector-init-done
    _debug_report(
        "D",
        "cli.py:_run_pipeline",
        "Detector YOLO selesai diinisialisasi",
        {"model_path": cfg.model.path},
    )
    # #endregion
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

    # #region debug-point D:cli-capture-open-start
    _debug_report(
        "D",
        "cli.py:_run_pipeline",
        "Mulai membuka capture source",
        {"source": cfg.source, "camera_backend": cfg.camera.backend},
    )
    # #endregion
    capture, is_camera = _open_capture(cfg.source, cfg.camera)
    # #region debug-point D:cli-capture-open-done
    _debug_report(
        "D",
        "cli.py:_run_pipeline",
        "Capture source berhasil dibuka",
        {"source": cfg.source, "is_camera": is_camera},
    )
    # #endregion

    fps = capture.get(cv2.CAP_PROP_FPS) or cfg.camera.fps or 30.0
    if fps <= 1.0:
        fps = cfg.camera.fps or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    live_started_at = time.perf_counter()
    last_loop_started_at = live_started_at

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
    last_overlay_speed_by_track: dict[int, float | None] = {}

    # #region debug-point D:cli-pipeline-start
    _debug_report(
        "D",
        "cli.py:_run_pipeline",
        "Pipeline deteksi dimulai",
        {
            "source": cfg.source,
            "is_camera": is_camera,
            "fps": round(float(fps), 3),
            "width": width,
            "height": height,
            "skip_frames": cfg.skip_frames,
            "display": cfg.display,
            "real_distance_meters": cfg.speed.real_distance_meters,
        },
    )
    # #endregion
    if cfg.display:
        typer.echo("Preview aktif. Tekan q, Esc, atau tutup jendela preview untuk berhenti.")

    try:
        while True:
            if _STOP_REQUESTED:
                # #region debug-point B:ctrlc-stop-flag-loop
                _debug_report(
                    "B",
                    "cli.py:_run_pipeline",
                    "Loop berhenti karena stop flag aktif",
                    {"frame_index": frame_index, "processed_frames": processed_frames},
                )
                # #endregion
                break
            loop_started_at = time.perf_counter()
            if frame_index == 0:
                # #region debug-point A:ctrlc-loop-enter
                _debug_report(
                    "A",
                    "cli.py:_run_pipeline",
                    "Masuk ke loop utama pipeline kamera",
                    {"display": cfg.display, "source": cfg.source},
                )
                # #endregion
            ok, frame = capture.read()
            read_elapsed_sec = time.perf_counter() - loop_started_at
            if not ok:
                # #region debug-point D:cli-capture-ended
                _debug_report(
                    "D",
                    "cli.py:_run_pipeline",
                    "Capture.read berhenti mengirim frame",
                    {"frame_index": frame_index, "processed_frames": processed_frames},
                )
                # #endregion
                break

            if is_camera:
                frame = _apply_camera_transforms(frame, cfg.camera)

            if _STOP_REQUESTED:
                # #region debug-point B:ctrlc-stop-after-read
                _debug_report(
                    "B",
                    "cli.py:_run_pipeline",
                    "Stop flag aktif setelah capture.read",
                    {"frame_index": frame_index, "processed_frames": processed_frames},
                )
                # #endregion
                break

            frame_index += 1
            if cfg.skip_frames and (frame_index - 1) % (cfg.skip_frames + 1) != 0:
                continue

            predict_started_at = time.perf_counter()
            detections = detector.predict(frame)
            predict_elapsed_sec = time.perf_counter() - predict_started_at
            if _STOP_REQUESTED:
                # #region debug-point B:ctrlc-stop-after-predict
                _debug_report(
                    "B",
                    "cli.py:_run_pipeline",
                    "Stop flag aktif setelah inferensi detector",
                    {"frame_index": frame_index, "processed_frames": processed_frames},
                )
                # #endregion
                break
            active_tracks = tracker.update(detections)
            if is_camera:
                timestamp_sec = time.perf_counter() - live_started_at
            else:
                timestamp_sec = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if timestamp_sec <= 0:
                timestamp_sec = processed_frames / fps

            if processed_frames < 5 or processed_frames % 15 == 0:
                # #region debug-point D:cli-frame-summary
                _debug_report(
                    "D",
                    "cli.py:_run_pipeline",
                    "Ringkasan frame pipeline",
                    {
                        "frame_index": frame_index,
                        "processed_frames": processed_frames,
                        "detections": len(detections),
                        "active_tracks": len(active_tracks),
                        "timestamp_sec": round(timestamp_sec, 4),
                        "read_elapsed_sec": round(read_elapsed_sec, 4),
                        "predict_elapsed_sec": round(predict_elapsed_sec, 4),
                        "loop_delta_sec": round(loop_started_at - last_loop_started_at, 4),
                    },
                )
                # #endregion

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
                _draw_track(frame, track, state.speed_kmh, state.direction)
                if last_overlay_speed_by_track.get(track.track_id) != state.speed_kmh:
                    # #region debug-point E:cli-overlay-update
                    _debug_report(
                        "E",
                        "cli.py:_run_pipeline",
                        "Overlay track diperbarui dengan state kecepatan terbaru",
                        {
                            "track_id": track.track_id,
                            "label": track.label,
                            "speed_kmh": None if state.speed_kmh is None else round(state.speed_kmh, 3),
                            "direction": state.direction,
                        },
                    )
                    # #endregion
                    last_overlay_speed_by_track[track.track_id] = state.speed_kmh

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
                    # #region debug-point E:cli-event-written
                    _debug_report(
                        "E",
                        "cli.py:_run_pipeline",
                        "Event kecepatan ditulis ke CSV",
                        {
                            "track_id": event.track_id,
                            "direction": event.direction,
                            "speed_kmh": round(event.speed_kmh, 3),
                            "elapsed_seconds": round(event.elapsed_seconds, 6),
                            "recorded_events": recorded_events,
                        },
                    )
                    # #endregion

            processed_frames += 1

            if writer is not None:
                writer.write(frame)

            if cfg.display:
                cv2.imshow("cardetec", frame)
                try:
                    window_visible = cv2.getWindowProperty("cardetec", cv2.WND_PROP_VISIBLE)
                except cv2.error:
                    window_visible = 0
                if window_visible < 1:
                    # #region debug-point B:ctrlc-stop-from-window-close
                    _debug_report(
                        "B",
                        "cli.py:_run_pipeline",
                        "Permintaan stop karena jendela preview ditutup",
                        {"window_visible": window_visible},
                    )
                    # #endregion
                    _STOP_REQUESTED = True
                    break
                pressed_key = cv2.waitKey(1) & 0xFF
                if pressed_key in (ord("q"), 27):
                    # #region debug-point B:ctrlc-stop-from-preview-key
                    _debug_report(
                        "B",
                        "cli.py:_run_pipeline",
                        "Permintaan stop dari tombol preview",
                        {"key_code": pressed_key},
                    )
                    # #endregion
                    _STOP_REQUESTED = True
                    break

            if cfg.max_frames is not None and processed_frames >= cfg.max_frames:
                break
            last_loop_started_at = loop_started_at
    except KeyboardInterrupt:
        # #region debug-point B:ctrlc-keyboard-interrupt
        _debug_report(
            "B",
            "cli.py:_run_pipeline",
            "KeyboardInterrupt tertangkap di pipeline",
            {"frame_index": frame_index, "processed_frames": processed_frames, "display": cfg.display},
        )
        # #endregion
        raise
    finally:
        # #region debug-point E:ctrlc-finally-enter
        _debug_report(
            "E",
            "cli.py:_run_pipeline",
            "Masuk ke blok finally untuk cleanup capture",
            {"frame_index": frame_index, "processed_frames": processed_frames},
        )
        # #endregion
        capture.release()
        # #region debug-point E:ctrlc-capture-released
        _debug_report(
            "E",
            "cli.py:_run_pipeline",
            "capture.release selesai dijalankan",
            {"source": cfg.source},
        )
        # #endregion
        if writer is not None:
            writer.release()
            # #region debug-point E:ctrlc-writer-released
            _debug_report(
                "E",
                "cli.py:_run_pipeline",
                "writer.release selesai dijalankan",
                {"output_video": cfg.output_video},
            )
            # #endregion
        if event_file is not None:
            event_file.close()
            # #region debug-point E:ctrlc-event-file-closed
            _debug_report(
                "E",
                "cli.py:_run_pipeline",
                "File event CSV berhasil ditutup",
                {"output_events_csv": cfg.output_events_csv},
            )
            # #endregion
        if cfg.display:
            # #region debug-point A:ctrlc-destroy-windows-start
            _debug_report(
                "A",
                "cli.py:_run_pipeline",
                "Mulai memanggil cv2.destroyAllWindows",
                {"display": cfg.display},
            )
            # #endregion
            cv2.destroyAllWindows()
            # #region debug-point E:ctrlc-destroy-windows-done
            _debug_report(
                "E",
                "cli.py:_run_pipeline",
                "cv2.destroyAllWindows selesai dijalankan",
                {"display": cfg.display},
            )
            # #endregion

    typer.echo(f"Selesai. Frame diproses: {processed_frames}. Event kecepatan: {recorded_events}.")
    if cfg.output_video:
        typer.echo(f"Video keluaran: {cfg.output_video}")
    if cfg.output_events_csv:
        typer.echo(f"CSV event: {cfg.output_events_csv}")


if __name__ == "__main__":
    app()
