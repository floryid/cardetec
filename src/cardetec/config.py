from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class LineConfig:
    name: str
    start: tuple[int, int]
    end: tuple[int, int]
    color_bgr: tuple[int, int, int] = (0, 255, 255)


@dataclass(slots=True)
class ModelConfig:
    path: str = ""
    input_size: int = 640
    score_threshold: float = 0.25
    confidence_threshold: float = 0.25
    nms_threshold: float = 0.45
    labels: list[str] = field(default_factory=list)
    allowed_classes: list[str] = field(default_factory=lambda: ["car", "bus", "truck", "motorcycle"])


@dataclass(slots=True)
class TrackingConfig:
    max_distance: float = 90.0
    max_missing_frames: int = 30
    min_confirmed_hits: int = 3
    trail_size: int = 24


@dataclass(slots=True)
class CameraConfig:
    backend: str = "auto"
    width: int = 1280
    height: int = 720
    fps: float = 30.0
    warmup_frames: int = 8
    flip_horizontal: bool = False
    flip_vertical: bool = False
    retry_open_count: int = 2


@dataclass(slots=True)
class SpeedConfig:
    real_distance_meters: float = 12.0
    line_a: LineConfig = field(
        default_factory=lambda: LineConfig("A", (120, 260), (520, 260), (0, 255, 255))
    )
    line_b: LineConfig = field(
        default_factory=lambda: LineConfig("B", (120, 360), (520, 360), (0, 165, 255))
    )
    min_speed_kmh: float = 1.0
    max_speed_kmh: float = 220.0


@dataclass(slots=True)
class AppConfig:
    source: str | int
    output_video: str | None = "outputs/result.mp4"
    output_events_csv: str | None = "outputs/events.csv"
    display: bool = True
    skip_frames: int = 0
    max_frames: int | None = None
    camera: CameraConfig = field(default_factory=CameraConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    speed: SpeedConfig = field(default_factory=SpeedConfig)


def create_default_config(preset: str = "video") -> AppConfig:
    preset_name = preset.lower()
    if preset_name == "camera":
        return AppConfig(
            source=0,
            output_video="outputs/camera_result.mp4",
            output_events_csv="outputs/camera_events.csv",
            display=True,
            camera=CameraConfig(
                backend="dshow",
                width=1280,
                height=720,
                fps=30.0,
                warmup_frames=10,
                retry_open_count=3,
            ),
            model=ModelConfig(path="models/yolov8n.onnx"),
            tracking=TrackingConfig(max_missing_frames=20, min_confirmed_hits=2),
            speed=SpeedConfig(
                real_distance_meters=6.0,
                line_a=LineConfig("A", (200, 250), (1080, 250), (0, 255, 255)),
                line_b=LineConfig("B", (200, 430), (1080, 430), (0, 165, 255)),
            ),
        )

    if preset_name == "termux":
        return AppConfig(
            source="/sdcard/Download/traffic.mp4",
            output_video="outputs/termux_result.mp4",
            output_events_csv="outputs/termux_events.csv",
            display=False,
            skip_frames=1,
            camera=CameraConfig(backend="auto"),
            model=ModelConfig(path="models/yolov8n.onnx"),
            tracking=TrackingConfig(max_distance=85.0, max_missing_frames=20, trail_size=20),
            speed=SpeedConfig(
                real_distance_meters=12.0,
                line_a=LineConfig("A", (120, 260), (520, 260), (0, 255, 255)),
                line_b=LineConfig("B", (120, 360), (520, 360), (0, 165, 255)),
            ),
        )

    return AppConfig(
        source="samples/traffic.mp4",
        output_video="outputs/result.mp4",
        output_events_csv="outputs/events.csv",
        display=True,
        camera=CameraConfig(backend="auto"),
        model=ModelConfig(path="models/yolov8n.onnx"),
    )


def _parse_line(name: str, payload: dict) -> LineConfig:
    return LineConfig(
        name=payload.get("name", name),
        start=tuple(payload["start"]),
        end=tuple(payload["end"]),
        color_bgr=tuple(payload.get("color_bgr", (0, 255, 255))),
    )


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    model_raw = raw.get("model", {})
    tracking_raw = raw.get("tracking", {})
    camera_raw = raw.get("camera", {})
    speed_raw = raw.get("speed", {})

    model = ModelConfig(
        path=model_raw["path"],
        input_size=model_raw.get("input_size", 640),
        score_threshold=model_raw.get("score_threshold", 0.25),
        confidence_threshold=model_raw.get("confidence_threshold", 0.25),
        nms_threshold=model_raw.get("nms_threshold", 0.45),
        labels=model_raw.get("labels", []),
        allowed_classes=model_raw.get("allowed_classes", ["car", "bus", "truck", "motorcycle"]),
    )

    tracking = TrackingConfig(
        max_distance=tracking_raw.get("max_distance", 90.0),
        max_missing_frames=tracking_raw.get("max_missing_frames", 30),
        min_confirmed_hits=tracking_raw.get("min_confirmed_hits", 3),
        trail_size=tracking_raw.get("trail_size", 24),
    )

    camera = CameraConfig(
        backend=camera_raw.get("backend", "auto"),
        width=camera_raw.get("width", 1280),
        height=camera_raw.get("height", 720),
        fps=camera_raw.get("fps", 30.0),
        warmup_frames=camera_raw.get("warmup_frames", 8),
        flip_horizontal=camera_raw.get("flip_horizontal", False),
        flip_vertical=camera_raw.get("flip_vertical", False),
        retry_open_count=camera_raw.get("retry_open_count", 2),
    )

    speed = SpeedConfig(
        real_distance_meters=speed_raw.get("real_distance_meters", 12.0),
        line_a=_parse_line("A", speed_raw.get("line_a", {"start": [120, 260], "end": [520, 260]})),
        line_b=_parse_line("B", speed_raw.get("line_b", {"start": [120, 360], "end": [520, 360]})),
        min_speed_kmh=speed_raw.get("min_speed_kmh", 1.0),
        max_speed_kmh=speed_raw.get("max_speed_kmh", 220.0),
    )

    return AppConfig(
        source=raw["source"],
        output_video=raw.get("output_video", "outputs/result.mp4"),
        output_events_csv=raw.get("output_events_csv", "outputs/events.csv"),
        display=raw.get("display", True),
        skip_frames=raw.get("skip_frames", 0),
        max_frames=raw.get("max_frames"),
        camera=camera,
        model=model,
        tracking=tracking,
        speed=speed,
    )


def save_config(config: AppConfig, config_path: str | Path) -> Path:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "source": config.source,
        "output_video": config.output_video,
        "output_events_csv": config.output_events_csv,
        "display": config.display,
        "skip_frames": config.skip_frames,
        "max_frames": config.max_frames,
        "camera": {
            "backend": config.camera.backend,
            "width": config.camera.width,
            "height": config.camera.height,
            "fps": config.camera.fps,
            "warmup_frames": config.camera.warmup_frames,
            "flip_horizontal": config.camera.flip_horizontal,
            "flip_vertical": config.camera.flip_vertical,
            "retry_open_count": config.camera.retry_open_count,
        },
        "model": {
            "path": config.model.path,
            "input_size": config.model.input_size,
            "score_threshold": config.model.score_threshold,
            "confidence_threshold": config.model.confidence_threshold,
            "nms_threshold": config.model.nms_threshold,
            "labels": config.model.labels,
            "allowed_classes": config.model.allowed_classes,
        },
        "tracking": {
            "max_distance": config.tracking.max_distance,
            "max_missing_frames": config.tracking.max_missing_frames,
            "min_confirmed_hits": config.tracking.min_confirmed_hits,
            "trail_size": config.tracking.trail_size,
        },
        "speed": {
            "real_distance_meters": config.speed.real_distance_meters,
            "min_speed_kmh": config.speed.min_speed_kmh,
            "max_speed_kmh": config.speed.max_speed_kmh,
            "line_a": {
                "name": config.speed.line_a.name,
                "start": list(config.speed.line_a.start),
                "end": list(config.speed.line_a.end),
                "color_bgr": list(config.speed.line_a.color_bgr),
            },
            "line_b": {
                "name": config.speed.line_b.name,
                "start": list(config.speed.line_b.start),
                "end": list(config.speed.line_b.end),
                "color_bgr": list(config.speed.line_b.color_bgr),
            },
        },
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return path
