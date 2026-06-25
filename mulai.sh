#!/data/data/com.termux/files/usr/bin/bash
set -e

cd "$(dirname "$0")"

if [ "$#" -eq 0 ]; then
  python jalan.py termux
else
  python jalan.py "$@"
fi
