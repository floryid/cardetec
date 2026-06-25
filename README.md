<div align="center">

# CarDetec

<p>
  <strong>Vehicle Detection and Speed Estimation with YOLO ONNX + OpenCV DNN</strong><br>
  <strong>Deteksi Kendaraan dan Estimasi Kecepatan dengan YOLO ONNX + OpenCV DNN</strong>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/OpenCV-DNN-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV">
  <img src="https://img.shields.io/badge/YOLO-ONNX-111827?style=for-the-badge&logo=onnx&logoColor=white" alt="YOLO ONNX">
  <img src="https://img.shields.io/badge/CLI-Typer-22C55E?style=for-the-badge" alt="Typer">
</p>

<p>
  <img src="https://img.shields.io/badge/Desktop-Windows%20%7C%20Linux%20%7C%20macOS-0EA5E9?style=flat-square" alt="Desktop">
  <img src="https://img.shields.io/badge/Android-Termux-F97316?style=flat-square" alt="Termux">
  <img src="https://img.shields.io/badge/Use%20Case-Automotive%20%7C%20Research%20%7C%20CCTV-111827?style=flat-square" alt="Use Case">
  <img src="https://img.shields.io/badge/License-MIT-10B981?style=flat-square" alt="MIT">
</p>

</div>

---

## Global Overview
**English**

CarDetec is a lightweight Python application for vehicle detection, object tracking, and line-based speed estimation. It is designed for traffic demos, automotive analysis, CCTV experiments, and portable workflows on desktop or Android Termux.

**Indonesia**

CarDetec adalah aplikasi Python ringan untuk deteksi kendaraan, tracking objek, dan estimasi kecepatan berbasis dua garis ukur. Proyek ini dirancang untuk demo lalu lintas, analisis otomotif, eksperimen CCTV, dan workflow portabel di desktop maupun Android Termux.

## Why CarDetec
| Feature | English | Indonesia |
|---|---|---|
| Vehicle Detection | Detects `car`, `bus`, `truck`, and `motorcycle` classes | Mendeteksi kelas `car`, `bus`, `truck`, dan `motorcycle` |
| Speed Estimation | Computes vehicle speed from two calibrated lines | Menghitung kecepatan kendaraan dari dua garis kalibrasi |
| Camera Ready | Supports webcam, USB camera, and video files | Mendukung webcam, USB camera, dan file video |
| Termux Friendly | Can run in Android Termux without desktop GUI | Dapat berjalan di Android Termux tanpa GUI desktop |
| Simple Launcher | Includes short launcher commands for quick use | Menyediakan launcher singkat agar mudah dijalankan |
| GitHub Ready | Clean project structure for sharing and deployment | Struktur proyek rapi untuk dibagikan dan dipublikasikan |

## Quick Start
**English**

If you want to try the project quickly on desktop:

```bash
git clone https://github.com/floryid/cardetec.git
cd cardetec
pip install -r requirements-desktop.txt
python jalan.py
```

**Indonesia**

Jika ingin langsung mencoba di desktop:

```bash
git clone https://github.com/floryid/cardetec.git
cd cardetec
pip install -r requirements-desktop.txt
python jalan.py
```

## Easiest Way
**English**

After installing dependencies, use the short launcher so you do not need long CLI commands.

```bash
python jalan.py
python jalan.py kamera
python jalan.py cek
python jalan.py scan
python jalan.py termux
```

**Indonesia**

Setelah dependency terpasang, gunakan launcher singkat agar tidak perlu mengetik command panjang.

```bash
python jalan.py
python jalan.py kamera
python jalan.py cek
python jalan.py scan
python jalan.py termux
```

**Windows**

```bash
mulai.bat
mulai.bat cek
```

**Linux / Termux**

```bash
bash mulai.sh
bash mulai.sh cek
```

## Launcher Modes
| Command | English | Indonesia |
|---|---|---|
| `python jalan.py` | Auto default mode, optimized for easy startup | Mode default otomatis, dioptimalkan agar mudah dijalankan |
| `python jalan.py kamera` | Standard desktop camera mode | Mode kamera desktop standar |
| `python jalan.py termux` | Android Termux preset without GUI preview | Preset Android Termux tanpa preview GUI |
| `python jalan.py video file.mp4` | Run a specific video file quickly | Jalankan file video tertentu dengan cepat |
| `python jalan.py cek` | Check camera and model readiness | Cek kesiapan kamera dan model |
| `python jalan.py scan` | Scan available camera devices | Scan camera device yang tersedia |

## Automotive Use Cases
**English**

CarDetec is suitable for automotive demos, traffic research, roadside observation, prototype enforcement systems, and speed analysis experiments.

**Indonesia**

CarDetec cocok untuk demo otomotif, riset lalu lintas, observasi jalan, prototipe sistem penegakan, dan eksperimen analisis kecepatan kendaraan.

## Detection Flow
```text
Camera / Video
      |
      v
YOLO ONNX Detection
      |
      v
Centroid Tracking
      |
      v
Cross Line A -> B
      |
      v
Speed Estimation (km/h)
      |
      v
Annotated Video + CSV Events
```

**Formula / Rumus**

```text
speed (km/h) = (distance_meters / time_seconds) * 3.6
```

## Overlay Style
**English**

The overlay is intentionally minimal so the user can focus on each detected vehicle and its speed label.

**Indonesia**

Overlay dibuat minimal agar pengguna fokus pada tiap kendaraan yang terdeteksi dan label kecepatannya.

- Vehicle box per object
- Speed label appears only when the speed is already measured
- ID and object label stay compact
- CSV speed events remain available
- Suitable for demos, field tests, and automotive content

## Installation
### Desktop
**English**

Create a virtual environment and install desktop dependencies:

```bash
python -m venv .venv
```

**Windows**

```bash
.venv\Scripts\activate
```

**Linux/macOS**

```bash
source .venv/bin/activate
```

```bash
pip install --upgrade pip
pip install -r requirements-desktop.txt
```

**Optional development tools / Opsional untuk development**

```bash
pip install -e .[dev]
```

### Termux
**English**

The Termux workflow uses `OpenCV DNN + ONNX` so it stays lighter than a full desktop PyTorch setup.

**Indonesia**

Workflow Termux memakai `OpenCV DNN + ONNX` agar lebih ringan dibanding setup PyTorch desktop penuh.

**Manual setup**

```bash
pkg update && pkg upgrade
pkg install python git ffmpeg opencv-python python-numpy
pip install --upgrade pip
pip install -r requirements-termux.txt
pip install -e . --no-deps
termux-setup-storage
```

**Easy setup**

```bash
bash install-termux.sh
```

**Run after install**

```bash
bash mulai.sh
```

**Run Android video**

```bash
bash mulai.sh video /sdcard/Download/traffic.mp4
```

**Useful Termux commands**

```bash
python jalan.py termux
python jalan.py bantuan
```

**References / Referensi**

- [Termux Python Wiki](https://wiki.termux.com/wiki/Python)
- [termux-packages issue #25847](https://github.com/termux/termux-packages/issues/25847)

## Model Setup
**English**

The ONNX model is not stored in the repository to keep the project lightweight.

**Indonesia**

Model ONNX tidak disimpan di repository agar ukuran proyek tetap ringan.

Save the model at:

```text
models/yolov8n.onnx
```

If you have `yolov8n.pt`, export it to ONNX:

```bash
pip install ultralytics
yolo export model=yolov8n.pt imgsz=640 format=onnx opset=12
```

Reference:

- [Ultralytics YOLOv8 OpenCV ONNX Example](https://github.com/ultralytics/ultralytics/blob/main/examples/YOLOv8-OpenCV-ONNX-Python/README.md)

## Camera And Video Usage
**Scan camera**

Windows:

```bash
cardetec cameras --max-devices 5 --backend dshow
```

Linux:

```bash
cardetec cameras --max-devices 5 --backend v4l2
```

**Validate camera and model**

```bash
cardetec doctor --config configs/camera.yaml --check-camera
```

**Run default webcam**

```bash
cardetec run --config configs/camera.yaml
```

**Run low-power mode**

```bash
cardetec run --config configs/camera-low-power.yaml
```

**Generate config automatically**

```bash
cardetec init-config --preset camera --output configs/local-camera.yaml --source 1
```

## Available Configs
| Config | English | Indonesia |
|---|---|---|
| `configs/default.yaml` | Desktop video preset | Preset video desktop |
| `configs/camera.yaml` | Webcam or USB camera preset | Preset webcam atau USB camera |
| `configs/camera-low-power.yaml` | Lighter camera preset for modest hardware | Preset kamera ringan untuk perangkat menengah |
| `configs/termux.yaml` | Android Termux and mobile video preset | Preset Android Termux dan video mobile |

## Important Parameters
| Parameter | English | Indonesia |
|---|---|---|
| `source` | Video path or camera index like `0`, `1`, `2` | Path video atau index kamera seperti `0`, `1`, `2` |
| `output_video` | Output annotated video path | Lokasi hasil video anotasi |
| `output_events_csv` | CSV path for recorded speed events | Lokasi CSV event kecepatan |
| `display` | Enable or disable OpenCV preview | Menyalakan atau mematikan preview OpenCV |
| `skip_frames` | Skip frames to reduce compute load | Melewati frame untuk menurunkan beban komputasi |
| `camera.backend` | OpenCV backend such as `dshow`, `msmf`, `v4l2`, `auto` | Backend OpenCV seperti `dshow`, `msmf`, `v4l2`, `auto` |
| `camera.width`, `camera.height` | Target capture resolution | Resolusi target capture |
| `camera.fps` | Target webcam FPS | FPS target untuk webcam |
| `camera.warmup_frames` | Initial frames discarded for camera stability | Frame awal yang dibuang agar kamera stabil |
| `camera.flip_horizontal` | Flip frame horizontally | Membalik frame secara horizontal |
| `model.path` | YOLO ONNX model path | Path model YOLO ONNX |
| `speed.real_distance_meters` | Real-world distance between line A and line B | Jarak nyata antara garis A dan garis B |
| `speed.line_a`, `speed.line_b` | Measuring line coordinates | Koordinat garis pengukuran |

## CLI Commands
```bash
cardetec run --config configs/camera.yaml
cardetec cameras --max-devices 5 --backend dshow
cardetec doctor --config configs/camera.yaml --check-camera
cardetec init-config --preset camera --output configs/local-camera.yaml
```

| Command | English | Indonesia |
|---|---|---|
| `run` | Run detection and speed estimation | Menjalankan deteksi dan estimasi kecepatan |
| `cameras` | Scan available cameras | Scan camera yang tersedia |
| `doctor` | Validate environment and config | Validasi environment dan config |
| `init-config` | Generate config from a preset | Generate config dari preset |

## Project Structure
```text
cardetec/
├── .github/workflows/ci.yml
├── configs/
│   ├── default.yaml
│   ├── camera.yaml
│   ├── camera-low-power.yaml
│   └── termux.yaml
├── models/
│   └── README.md
├── outputs/
├── samples/
├── src/cardetec/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── speed.py
│   ├── tracker.py
│   └── yolo_onnx.py
├── tests/
│   ├── test_config.py
│   └── test_speed.py
├── install-termux.sh
├── jalan.py
├── mulai.bat
├── mulai.sh
├── pyproject.toml
├── requirements-desktop.txt
└── requirements-termux.txt
```

## Example CSV Output
```csv
track_id,label,direction,speed_kmh,elapsed_seconds,frame
3,car,A->B,42.15,1.025,188
8,truck,B->A,37.90,1.140,263
```

## Calibration Tips
**English**

- Use a static camera, not a handheld recording
- Place the two lines where vehicles clearly cross them
- Measure the real-world distance between both lines
- Match the line placement to the road perspective
- Test several videos until crossing events are stable

**Indonesia**

- Gunakan kamera statis, jangan handheld
- Tempatkan dua garis pada jalur yang benar-benar dilintasi kendaraan
- Ukur jarak nyata antara kedua garis
- Sesuaikan posisi garis dengan perspektif jalan
- Uji beberapa video sampai crossing stabil

## Testing
```bash
python -m pytest -q
```

## Linting
```bash
python -m ruff check .
```

## Current Limitations
| English | Indonesia |
|---|---|
| The tracker is still centroid-based, not ByteTrack or DeepSORT | Tracker masih berbasis centroid, belum ByteTrack atau DeepSORT |
| Speed accuracy strongly depends on line calibration | Akurasi kecepatan sangat bergantung pada kalibrasi garis |
| There is no perspective correction or homography mapping yet | Belum ada perspective correction atau homography mapping |
| Best suited for demos, prototypes, and stable CCTV angles | Paling cocok untuk demo, prototipe, dan CCTV dengan sudut stabil |

## Roadmap
| English | Indonesia |
|---|---|
| RTSP / IP camera support | Dukungan RTSP / IP camera |
| FastAPI web dashboard | Dashboard web FastAPI |
| Vehicle violation snapshots | Snapshot pelanggaran kendaraan |
| JSON event export | Export event JSON |
| Stronger tracker | Tracker yang lebih kuat |
| Perspective-based 4-point calibration | Kalibrasi 4 titik berbasis perspektif |

## License
MIT
