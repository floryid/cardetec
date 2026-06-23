# CarDetec

Aplikasi Python modern untuk deteksi kendaraan dan estimasi kecepatan berbasis YOLO ONNX + OpenCV DNN. Proyek ini dibuat agar:

- rapi untuk di-push ke GitHub,
- ringan dibanding runtime berbasis PyTorch,
- tetap realistis dijalankan di desktop dan Termux,
- mudah dikalibrasi memakai dua garis pengukuran.

## Fitur

- Deteksi kendaraan dari video memakai model YOLO format `.onnx`
- Filter kelas kendaraan: `car`, `bus`, `truck`, `motorcycle`
- Tracking sederhana berbasis centroid
- Estimasi kecepatan saat kendaraan melintasi dua garis kalibrasi
- Output video beranotasi
- Output event kecepatan ke file CSV
- Konfigurasi YAML terpisah untuk desktop dan Termux
- Preset khusus camera device atau webcam
- Command bantu `cameras`, `doctor`, dan `init-config`
- GitHub Actions untuk menjalankan test otomatis

## Struktur Proyek

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
│   ├── cli.py
│   ├── config.py
│   ├── speed.py
│   ├── tracker.py
│   └── yolo_onnx.py
├── tests/test_speed.py
├── .gitignore
├── pyproject.toml
├── README.md
└── requirements-desktop.txt
```

## Cara Kerja

1. Video dibaca frame per frame.
2. Model YOLO ONNX mendeteksi kendaraan.
3. Tracker menghubungkan kendaraan antar frame.
4. Saat pusat objek melintasi garis `A` lalu `B`, sistem menghitung selisih waktu.
5. Kecepatan dihitung dengan rumus:

```text
kecepatan (km/h) = (jarak_meter / waktu_detik) * 3.6
```

Supaya hasil akurat, jarak riil antara garis `A` dan `B` harus Anda ukur di lokasi sebenarnya.

## Persiapan Model YOLO

Repo ini tidak menyertakan file model karena ukurannya besar. Simpan model di:

```text
models/yolov8n.onnx
```

Jika Anda punya model `yolov8n.pt`, ekspor ke ONNX dengan Ultralytics:

```bash
pip install ultralytics
yolo export model=yolov8n.pt imgsz=640 format=onnx opset=12
```

Perintah ini mengikuti pola yang direkomendasikan pada contoh resmi Ultralytics untuk YOLO ONNX + OpenCV:
[Ultralytics YOLOv8 OpenCV ONNX Example](https://github.com/ultralytics/ultralytics/blob/main/examples/YOLOv8-OpenCV-ONNX-Python/README.md)

Setelah file `.onnx` jadi, pindahkan ke folder `models/`.

## Quick Start

Jika Anda ingin aplikasi cepat langsung jalan di laptop atau PC:

1. install dependensi,
2. letakkan model `models/yolov8n.onnx`,
3. scan kamera dengan `cardetec cameras`,
4. cek setup dengan `cardetec doctor --config configs/camera.yaml --check-camera`,
5. jalankan `cardetec run --config configs/camera.yaml`.

Urutan ini sengaja dibuat agar Anda bisa tahu lebih dulu apakah model, config, dan camera device sudah siap.

## Instalasi Desktop

### 1. Clone repo

```bash
git clone https://github.com/username/cardetec.git
cd cardetec
```

### 2. Buat virtual environment

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

### 3. Install dependensi

```bash
pip install --upgrade pip
pip install -r requirements-desktop.txt
```

Opsional untuk mode development:

```bash
pip install -e .[dev]
```

### 4. Siapkan video dan model

- Letakkan video contoh di `samples/traffic.mp4`
- Letakkan model di `models/yolov8n.onnx`

### 5. Jalankan aplikasi

```bash
cardetec run --config configs/default.yaml
```

### 6. Cek environment

```bash
cardetec doctor --config configs/default.yaml
```

## Menggunakan Camera Device

Versi terbaru aplikasi sudah ditingkatkan agar lebih cocok untuk webcam laptop atau kamera USB:

- `source` dapat berupa angka seperti `0`, `1`, atau `2`
- ada konfigurasi backend kamera seperti `dshow`, `msmf`, `v4l2`, atau `auto`
- bisa mengatur resolusi target, FPS target, warmup frame, dan flip gambar
- timestamp live camera memakai waktu nyata, bukan metadata file video

### Jalankan webcam default

```bash
cardetec run --config configs/camera.yaml
```

### Scan camera device lebih dulu

```bash
cardetec cameras --max-devices 5 --backend dshow
```

Jika Anda memakai Linux:

```bash
cardetec cameras --max-devices 5 --backend v4l2
```

### Jika kamera utama bukan device `0`

Ubah bagian ini:

```yaml
source: 1
```

### Preset untuk laptop biasa atau PC spek menengah

```bash
cardetec run --config configs/camera-low-power.yaml
```

Preset ini menurunkan resolusi, FPS, dan melewati sebagian frame agar inferensi lebih ringan.

### Opsi camera yang tersedia

```yaml
camera:
  backend: dshow
  width: 1280
  height: 720
  fps: 30.0
  warmup_frames: 10
  flip_horizontal: false
  flip_vertical: false
  retry_open_count: 3
```

Keterangan:

- `backend`: backend OpenCV untuk membuka kamera
- `width` dan `height`: resolusi target capture
- `fps`: target FPS kamera
- `warmup_frames`: jumlah frame awal yang dibuang agar exposure lebih stabil
- `flip_horizontal`: berguna jika webcam menampilkan preview seperti cermin
- `retry_open_count`: jumlah percobaan buka kamera jika device lambat siap

### Rekomendasi desktop Windows

- pakai `backend: dshow` lebih dulu
- jika gagal, coba `backend: msmf`
- gunakan resolusi `1280x720` atau `960x540` bila inferensi terasa berat
- letakkan dua garis kalibrasi di area jalan yang sering dilewati kendaraan

### Cek kesiapan camera config

```bash
cardetec doctor --config configs/camera.yaml --check-camera
```

Perintah ini mengecek:

- file config ada,
- YAML bisa dibaca,
- OpenCV tersedia,
- file model tersedia,
- kamera bisa dibuka jika `source` berupa device index.

### Generate config lokal otomatis

Jika Anda ingin membuat config baru tanpa mengedit file manual:

```bash
cardetec init-config --preset camera --output configs/local-camera.yaml --source 1
```

Untuk preset video:

```bash
cardetec init-config --preset video --output configs/local-video.yaml --source samples/traffic.mp4
```

### Rekomendasi laptop atau webcam

- gunakan tripod atau posisi kamera statis
- arahkan kamera ke jalan dari sudut yang konsisten
- hindari auto-focus berlebihan dan guncangan
- sesuaikan `skip_frames` jika CPU tidak kuat

## Instalasi di Termux

Pendekatan Termux pada repo ini sengaja memakai `OpenCV DNN + ONNX` agar tidak bergantung pada PyTorch desktop.

Menurut dokumentasi Termux, OpenCV Python sebaiknya dipasang dari package manager Termux, bukan dari `pip`, untuk menghindari error build:
[Termux Python Wiki](https://wiki.termux.com/wiki/Python)

Ada juga issue Termux yang menunjukkan `pip install opencv-python` bisa gagal dan solusi yang disarankan adalah memakai `pkg install opencv-python`:
[termux-packages issue #25847](https://github.com/termux/termux-packages/issues/25847)

### 1. Install paket sistem

```bash
pkg update && pkg upgrade
pkg install python git ffmpeg opencv-python python-numpy
```

### 2. Clone repo

```bash
git clone https://github.com/username/cardetec.git
cd cardetec
```

### 3. Install paket Python murni

```bash
pip install --upgrade pip
pip install -r requirements-termux.txt
pip install -e . --no-deps
```

Alasan memakai `--no-deps`: `numpy` dan `opencv-python` sudah dipenuhi dari paket Termux.

### 4. Beri akses storage

```bash
termux-setup-storage
```

### 5. Salin file video dan model

- video: `/sdcard/Download/traffic.mp4`
- model: `models/yolov8n.onnx`

### 6. Jalankan mode Termux

```bash
cardetec run --config configs/termux.yaml
```

### 7. Validasi setup Termux

```bash
cardetec doctor --config configs/termux.yaml
```

Catatan:

- `display: false` di config Termux karena `cv2.imshow()` biasanya tidak dipakai di Termux biasa.
- Hasil video dan CSV akan tersimpan di folder `outputs/`.

## Konfigurasi

Contoh file `configs/default.yaml`:

```yaml
source: samples/traffic.mp4
output_video: outputs/result.mp4
output_events_csv: outputs/events.csv
display: true

model:
  path: models/yolov8n.onnx

speed:
  real_distance_meters: 12.0
  line_a:
    start: [120, 260]
    end: [520, 260]
  line_b:
    start: [120, 360]
    end: [520, 360]
```

Parameter penting:

- `source`: path video atau index kamera, misalnya `0`
- `output_video`: lokasi video hasil anotasi
- `output_events_csv`: lokasi CSV event kecepatan
- `display`: tampilkan window OpenCV atau tidak
- `skip_frames`: lewati frame untuk mengurangi beban proses
- `camera.backend`: backend kamera OpenCV
- `camera.width`, `camera.height`, `camera.fps`: target capture untuk webcam
- `camera.warmup_frames`: buang beberapa frame awal agar kamera stabil
- `camera.flip_horizontal`, `camera.flip_vertical`: membalik frame live camera
- `model.path`: path model YOLO ONNX
- `speed.real_distance_meters`: jarak nyata antara garis `A` dan `B`
- `speed.line_a` dan `speed.line_b`: koordinat piksel dua garis pengukuran

## Command CLI

Command utama yang sekarang tersedia:

```bash
cardetec run --config configs/camera.yaml
cardetec cameras --max-devices 5 --backend dshow
cardetec doctor --config configs/camera.yaml --check-camera
cardetec init-config --preset camera --output configs/local-camera.yaml
```

Keterangan singkat:

- `run`: menjalankan deteksi kendaraan dan estimasi kecepatan
- `cameras`: scan device camera yang tersedia
- `doctor`: validasi environment, config, model, dan camera
- `init-config`: generate file config baru dari preset

## Supaya Langsung Bisa Dipakai

Checklist minimum:

- Python sudah terpasang
- OpenCV sudah terpasang
- `PyYAML` dan `typer` sudah terpasang
- model `models/yolov8n.onnx` sudah tersedia
- kamera atau video source tersedia
- garis `line_a` dan `line_b` sudah disesuaikan dengan sudut kamera Anda

Langkah paling praktis untuk webcam:

```bash
pip install -r requirements-desktop.txt
cardetec cameras --max-devices 5 --backend dshow
cardetec doctor --config configs/camera.yaml --check-camera
cardetec run --config configs/camera.yaml
```

## Contoh Output CSV

```csv
track_id,label,direction,speed_kmh,elapsed_seconds,frame
3,car,A->B,42.15,1.025,188
8,truck,B->A,37.90,1.140,263
```

## Menyesuaikan Kalibrasi Kecepatan

Supaya hasil lebih akurat:

- gunakan video statis, bukan kamera goyang,
- pilih dua garis yang memotong jalur kendaraan,
- ukur jarak riil antar garis di lapangan,
- sesuaikan `real_distance_meters`,
- sesuaikan posisi garis di config agar sejajar dengan area jalan,
- uji beberapa video dan lihat apakah crossing terjadi konsisten.

## Menjalankan Test

```bash
python -m pytest -q
```

## Cek Kualitas Kode

```bash
python -m ruff check .
```

## Deploy ke GitHub

1. Buat repository baru di GitHub.
2. Inisialisasi git lokal jika belum ada.
3. Commit semua file.
4. Push ke branch utama.

Contoh:

```bash
git init
git add .
git commit -m "feat: initial car speed detection app"
git branch -M main
git remote add origin https://github.com/username/cardetec.git
git push -u origin main
```

Setelah di-push, workflow `.github/workflows/ci.yml` akan menjalankan test otomatis pada setiap `push` dan `pull_request`.

## Batasan Saat Ini

- Tracking masih memakai centroid tracker sederhana, belum ByteTrack/DeepSORT.
- Akurasi kecepatan sangat bergantung pada kalibrasi garis dan kualitas video.
- Tanpa perspektif correction, hasil cocok untuk demo, prototipe, atau CCTV dengan sudut yang stabil.
- Untuk produksi, sebaiknya tambahkan homography/perspective mapping dan tracker yang lebih kuat.

## Pengembangan Lanjutan

Beberapa upgrade yang bisa Anda tambahkan:

- dukungan RTSP/IP camera,
- dashboard web dengan FastAPI,
- simpan snapshot pelanggaran,
- export JSON event,
- tracker ByteTrack,
- kalibrasi perspektif berbasis 4 titik,
- model custom hasil training sendiri.

## Lisensi

MIT
