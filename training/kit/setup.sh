#!/bin/bash -l
# One-time setup on a login node: Python environment plus pretrained weights.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/setup.sh
set -euo pipefail
source "$(dirname "$0")/env.sh"
# Python 3.12 or newer. Where the system Python is older (Kaggle, many GPU rental images), uv fetches 3.12.
if [[ ! -d "$FT_VENV" ]]; then
    if python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 12) else 1)'; then
        python3 -m venv "$FT_VENV"
    else
        echo "System Python is older than 3.12; getting 3.12 with uv."
        command -v uv >/dev/null || python3 -m pip install --quiet --user uv
        export PATH="$HOME/.local/bin:$PATH"
        uv venv --seed --python 3.12 "$FT_VENV"
    fi
fi
"$FT_VENV/bin/python" -c 'import sys; assert sys.version_info[:2] >= (3, 12), sys.version'
"$FT_VENV/bin/python" -m pip install --upgrade pip
"$FT_VENV/bin/python" -m pip install -r training/requirements.txt
"$FT_VENV/bin/python" -m pip check
"$FT_VENV/bin/python" -m pip freeze > "$FT_ROOT/installed-packages.txt"
cp training/requirements.txt "$FT_ROOT/installed-requirements.txt"
# Pre-download weights so GPU jobs never depend on the network.
"$FT_VENV/bin/python" -c 'import rfdetr; rfdetr.RFDETRSmall(); rfdetr.RFDETRMedium()'
mkdir -p weights
(cd weights && "$FT_VENV/bin/python" -c 'from ultralytics import YOLO; YOLO("yolov8s-oiv7.pt")')
echo "4663086e1b8edbc4202a9ec589b03195ed149ef8aa8beeb4b503e0e35ff1731a  weights/yolov8s-oiv7.pt" | sha256sum -c
ls -la "$RF_HOME" weights
echo "Setup complete."
