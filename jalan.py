from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cardetec.cli import app  # noqa: E402
from cardetec.config import create_default_config, save_config  # noqa: E402


HELP_TEXT = """CarDetec launcher singkat

Pakai salah satu:
  python jalan.py           -> jalankan mode default otomatis
  python jalan.py kamera    -> jalankan kamera normal
  python jalan.py termux    -> jalankan preset Termux
  python jalan.py video file.mp4 -> jalankan video pilihan
  python jalan.py cek       -> cek model dan kamera
  python jalan.py scan      -> scan kamera yang tersedia
  python jalan.py bantuan   -> tampilkan bantuan ini
"""


def _is_termux() -> bool:
    prefix = os.getenv("PREFIX", "")
    return "com.termux" in prefix or "termux" in prefix.lower()


def _default_run_args() -> list[str]:
    if _is_termux():
        return ["run", "--config", "configs/termux.yaml"]
    return ["run", "--config", "configs/camera-low-power.yaml"]


def _default_scan_backend() -> str:
    if sys.platform.startswith("win"):
        return "dshow"
    if _is_termux():
        return "auto"
    return "v4l2"


def _build_video_config(source_path: str) -> str:
    preset = "termux" if _is_termux() else "video"
    config = create_default_config(preset)
    config.source = source_path
    output_name = Path(source_path).stem or "video"
    config.output_video = f"outputs/{output_name}_result.mp4"
    config.output_events_csv = f"outputs/{output_name}_events.csv"
    output_path = ROOT_DIR / "configs" / "local-video.yaml"
    save_config(config, output_path)
    return str(output_path.relative_to(ROOT_DIR))


def _resolve_args(user_args: list[str]) -> list[str]:
    if not user_args:
        return _default_run_args()

    mode = user_args[0].lower()
    if mode in {"bantuan", "help", "-h", "--help"}:
        print(HELP_TEXT)
        raise SystemExit(0)
    if mode in {"kamera", "camera", "cam"}:
        return ["run", "--config", "configs/camera.yaml"]
    if mode in {"ringan", "low", "low-power"}:
        return ["run", "--config", "configs/camera-low-power.yaml"]
    if mode in {"termux", "android"}:
        return ["run", "--config", "configs/termux.yaml"]
    if mode in {"video", "file"}:
        if len(user_args) < 2:
            print("Format: python jalan.py video path_ke_video")
            raise SystemExit(1)
        return ["run", "--config", _build_video_config(user_args[1])]
    if mode in {"cek", "doctor"}:
        config_path = "configs/termux.yaml" if _is_termux() else "configs/camera.yaml"
        return ["doctor", "--config", config_path, "--check-camera"]
    if mode in {"scan", "cameras"}:
        return ["cameras", "--max-devices", "5", "--backend", _default_scan_backend()]

    return user_args


def main() -> None:
    sys.argv = [sys.argv[0], *_resolve_args(sys.argv[1:])]
    app()


if __name__ == "__main__":
    main()
