from pathlib import Path

from cardetec.config import create_default_config, load_config, save_config


def test_load_config_supports_camera_device_source(tmp_path: Path) -> None:
    config_file = tmp_path / "camera.yaml"
    config_file.write_text(
        """
source: 0
display: false
model:
  path: models/yolov8n.onnx
camera:
  backend: dshow
  width: 960
  height: 540
  fps: 25.0
  warmup_frames: 5
  flip_horizontal: true
  retry_open_count: 4
""".strip(),
        encoding="utf-8",
    )

    cfg = load_config(config_file)

    assert cfg.source == 0
    assert cfg.camera.backend == "dshow"
    assert cfg.camera.width == 960
    assert cfg.camera.height == 540
    assert cfg.camera.fps == 25.0
    assert cfg.camera.warmup_frames == 5
    assert cfg.camera.flip_horizontal is True
    assert cfg.camera.retry_open_count == 4


def test_create_and_save_camera_preset(tmp_path: Path) -> None:
    config = create_default_config("camera")
    output_file = tmp_path / "generated.yaml"

    written_path = save_config(config, output_file)
    loaded = load_config(written_path)

    assert written_path == output_file
    assert loaded.source == 0
    assert loaded.model.path == "models/yolov8n.onnx"
    assert loaded.camera.backend == "dshow"
    assert loaded.speed.real_distance_meters == 6.0


def test_create_and_save_termux_preset(tmp_path: Path) -> None:
    config = create_default_config("termux")
    output_file = tmp_path / "termux.yaml"

    written_path = save_config(config, output_file)
    loaded = load_config(written_path)

    assert written_path == output_file
    assert loaded.source == "/sdcard/Download/traffic.mp4"
    assert loaded.display is False
    assert loaded.skip_frames == 1
    assert loaded.camera.backend == "auto"
    assert loaded.output_video == "outputs/termux_result.mp4"
    assert loaded.output_events_csv == "outputs/termux_events.csv"
