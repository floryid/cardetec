#!/data/data/com.termux/files/usr/bin/bash
set -e

cd "$(dirname "$0")"

pkg update -y
pkg upgrade -y
pkg install -y python git ffmpeg opencv-python python-numpy

python -m pip install --upgrade pip
python -m pip install -r requirements-termux.txt
python -m pip install -e . --no-deps

termux-setup-storage

echo
echo "Instalasi selesai."
echo "Cara pakai:"
echo "  bash mulai.sh"
echo "  bash mulai.sh video /sdcard/Download/traffic.mp4"
echo "  python jalan.py bantuan"
