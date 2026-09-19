#!/usr/bin/env bash
# MARC Micromouse Simulator - one-click starter (macOS / Linux).
# Run:  chmod +x start.sh && ./start.sh
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 was not found. Install Python 3.10+ first."
    exit 1
fi

echo "[1/3] Python found: $(python3 --version)"
echo "[2/3] Installing dependencies (pygame)..."
python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install -r requirements.txt
echo "[3/3] Launching simulator..."
python3 main.py --2d
