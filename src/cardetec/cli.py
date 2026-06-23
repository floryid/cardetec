from __future__ import annotations

import csv
from pathlib import Path

import cv2
import typer

from .config import AppConfig, load_config
from .speed import SpeedEstimator
from .tracker import CentroidTracker, Track
from .yolo_onnx import YoloOnnxDetector


app = typer.Typer(add_completion=False, help="CLI deteksi kendaraan dan estimasi kecepatan.")


def _resolve_source(source: str) -> str | int:
    return int(source) if source.isdigit() else source


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


@app.command()
def run(
    config: str = typer.Option("configs/default.yaml", "--config", "-c", help="Path file YAML konfigurasi."),
) -> None:
    """Proses video dan hitung kecepatan kendaraan."""
    cfg = load_config(config)
    _run_pipeline(cfg)


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

    capture = cv2.VideoCapture(_resolve_source(cfg.source))
    if not capture.isOpened():
        raise typer.BadParameter(f"Tidak bisa membuka sumber video: {cfg.source}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)

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

            frame_index += 1
            if cfg.skip_frames and (frame_index - 1) % (cfg.skip_frames + 1) != 0:
                continue

            detections = detector.predict(frame)
            active_tracks = tracker.update(detections)
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
