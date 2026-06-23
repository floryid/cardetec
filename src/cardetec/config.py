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
    source: str
    output_video: str | None = "outputs/result.mp4"
    output_events_csv: str | None = "outputs/events.csv"
    display: bool = True
    skip_frames: int = 0
    max_frames: int | None = None
    model: ModelConfig = field(default_factory=ModelConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    speed: SpeedConfig = field(default_factory=SpeedConfig)


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
        model=model,
        tracking=tracking,
        speed=speed,
    )
