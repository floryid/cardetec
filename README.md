<div align="center">

# CarDetec

<p>
  <strong>Deteksi kendaraan dan estimasi kecepatan berbasis YOLO ONNX + OpenCV DNN</strong>
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
  <img src="https://img.shields.io/badge/License-MIT-10B981?style=flat-square" alt="MIT">
</p>

</div>

---

## Overview
CarDetec adalah aplikasi Python untuk mendeteksi kendaraan yang bergerak, melakukan tracking antar frame, lalu menghitung estimasi kecepatan saat kendaraan melintasi dua garis kalibrasi.

Proyek ini dirancang agar:

- ringan untuk CPU dengan `OpenCV DNN + ONNX`
- rapi untuk dipakai sebagai repo GitHub
- realistis dijalankan di desktop maupun Termux
- mudah dipakai dengan preset webcam dan utilitas CLI

## Highlights
| Fitur | Keterangan |
|---|---|
| Deteksi Kendaraan | Filter kelas `car`, `bus`, `truck`, `motorcycle` |
| Speed Estimation | Hitung kecepatan berdasarkan dua garis ukur |
| Camera Ready | Mendukung webcam, USB camera, dan file video |
| CLI Tools | Ada `run`, `cameras`, `doctor`, dan `init-config` |
| Multi Config | Preset desktop, low-power, dan Termux |
| GitHub Friendly | Struktur project bersih dan siap dipublish |

## Quick Start
Jika Anda ingin langsung mencoba dari webcam:

```bash
git clone https://github.com/floryid/cardetec.git
cd cardetec
pip install -r requirements-desktop.txt
cardetec cameras --max-devices 5 --backend dshow
cardetec doctor --config configs/camera.yaml --check-camera
cardetec run --config configs/camera.yaml
```

Untuk laptop atau PC spek menengah:

```bash
cardetec run --config configs/camera-low-power.yaml
```

## Demo Flow
Alur kerja aplikasi:

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

Rumus kecepatan:

```text
kecepatan (km/h) = (jarak_meter / waktu_detik) * 3.6
```

## Preview Style
Tampilan overlay aplikasi sekarang dibuat lebih modern dan mendekati gaya speed detection CCTV:

- judul hijau `YOLOV8 SPEED DETECTION`
- box kendaraan hijau
- label ID dan kecepatan di atas kendaraan
- garis atas hijau
- garis bawah merah
- output event kecepatan ke CSV

## Installation
### Desktop

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependency:

```bash
pip install --upgrade pip
pip install -r requirements-desktop.txt
```

Opsional untuk development:

```bash
pip install -e .[dev]
```

### Termux
Pendekatan Termux sengaja memakai `OpenCV DNN + ONNX` agar tidak bergantung pada PyTorch desktop.

```bash
pkg update && pkg upgrade
pkg install python git ffmpeg opencv-python python-numpy
pip install --upgrade pip
pip install -r requirements-termux.txt
pip install -e . --no-deps
termux-setup-storage
```

Referensi instalasi OpenCV di Termux:

- [Termux Python Wiki](https://wiki.termux.com/wiki/Python)
- [termux-packages issue #25847](https://github.com/termux/termux-packages/issues/25847)

## Model Setup
Model tidak disertakan ke repo agar ukuran repository tetap ringan.

Simpan model di:

```text
models/yolov8n.onnx
```

Jika Anda punya `yolov8n.pt`, ekspor ke ONNX:

```bash
pip install ultralytics
yolo export model=yolov8n.pt imgsz=640 format=onnx opset=12
```

Panduan referensi:

- [Ultralytics YOLOv8 OpenCV ONNX Example](https://github.com/ultralytics/ultralytics/blob/main/examples/YOLOv8-OpenCV-ONNX-Python/README.md)

## Camera Usage
CarDetec mendukung camera device secara langsung.

### Scan kamera
Windows:

```bash
cardetec cameras --max-devices 5 --backend dshow
```

Linux:

```bash
cardetec cameras --max-devices 5 --backend v4l2
```

### Validasi kamera dan model

```bash
cardetec doctor --config configs/camera.yaml --check-camera
```

### Jalankan webcam default

```bash
cardetec run --config configs/camera.yaml
```

### Jalankan mode ringan

```bash
cardetec run --config configs/camera-low-power.yaml
```

### Generate config otomatis

```bash
cardetec init-config --preset camera --output configs/local-camera.yaml --source 1
```

## Available Configs
| Config | Kegunaan |
|---|---|
| `configs/default.yaml` | Untuk file video desktop |
| `configs/camera.yaml` | Untuk webcam atau USB camera |
| `configs/camera-low-power.yaml` | Untuk laptop atau PC yang lebih ringan |
| `configs/termux.yaml` | Untuk Termux dan file video di Android |

## Important Parameters
| Parameter | Fungsi |
|---|---|
| `source` | Path video atau index kamera seperti `0`, `1`, `2` |
| `output_video` | Lokasi hasil video anotasi |
| `output_events_csv` | Lokasi CSV event kecepatan |
| `display` | Tampilkan preview OpenCV atau tidak |
| `skip_frames` | Lewati frame untuk menurunkan beban komputasi |
| `camera.backend` | Backend OpenCV seperti `dshow`, `msmf`, `v4l2`, `auto` |
| `camera.width`, `camera.height` | Resolusi target capture |
| `camera.fps` | FPS target untuk webcam |
| `camera.warmup_frames` | Frame awal yang dibuang agar kamera stabil |
| `camera.flip_horizontal` | Balik preview horizontal |
| `model.path` | Path model YOLO ONNX |
| `speed.real_distance_meters` | Jarak nyata antara garis A dan B |
| `speed.line_a`, `speed.line_b` | Posisi dua garis pengukuran |

## CLI Commands

```bash
cardetec run --config configs/camera.yaml
cardetec cameras --max-devices 5 --backend dshow
cardetec doctor --config configs/camera.yaml --check-camera
cardetec init-config --preset camera --output configs/local-camera.yaml
```

Ringkasannya:

- `run`: menjalankan deteksi dan estimasi kecepatan
- `cameras`: scan camera device
- `doctor`: validasi environment dan config
- `init-config`: generate config baru dari preset

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
Supaya hasil estimasi lebih akurat:

- gunakan kamera statis, jangan handheld
- pilih dua garis yang benar-benar memotong jalur kendaraan
- ukur jarak nyata antar garis di lokasi
- sesuaikan posisi garis dengan perspektif kamera
- uji beberapa video sampai crossing konsisten

## Testing

```bash
python -m pytest -q
```

## Linting

```bash
python -m ruff check .
```

## Current Limitations
- tracker masih centroid-based, belum ByteTrack atau DeepSORT
- akurasi kecepatan sangat bergantung pada kalibrasi garis
- belum ada perspective correction atau homography mapping
- paling cocok untuk demo, prototipe, dan CCTV dengan sudut stabil

## Roadmap
- dukungan RTSP / IP camera
- dashboard web FastAPI
- snapshot pelanggaran kendaraan
- export JSON event
- tracker yang lebih kuat
- kalibrasi 4 titik berbasis perspektif

## License
MIT
