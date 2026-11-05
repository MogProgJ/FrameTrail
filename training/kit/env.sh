# Shared settings for FrameTrail training. Source this; do not run it.
# On bwUniCluster it loads the Python module and works in the workspace. On any other Linux machine (a rented GPU
# VM, see training/README.md) it works in $FT_ROOT, default ~/frametrail-work, and needs python3.12 or newer.
if command -v ws_find >/dev/null 2>&1; then
    module load devel/miniforge/25.3.1-python-3.12
    FT_WS="$(ws_find frametrail)" || { echo "Workspace 'frametrail' not found; see training/README.md" >&2; return 1; }
    export FT_ROOT="$FT_WS/rf"
else
    export FT_ROOT="${FT_ROOT:-$HOME/frametrail-work}"
fi
export FT_VENV="$FT_ROOT/.venv"
export RF_HOME="$FT_ROOT/.cache/rfdetr"   # Official RF-DETR weights
export HF_HOME="$FT_ROOT/.cache/huggingface"
export TORCH_HOME="$FT_ROOT/.cache/torch"
export PIP_CACHE_DIR="$FT_ROOT/.cache/pip"
export YOLO_CONFIG_DIR="$FT_ROOT/.cache/ultralytics"
export PYTHONUNBUFFERED=1
export MPLBACKEND=Agg   # Notebook hosts (Kaggle, Colab) set a Jupyter-only plotting backend that this environment lacks
cd "$FT_ROOT" || { echo "Copy the training folder to $FT_ROOT first" >&2; return 1; }
mkdir -p "$YOLO_CONFIG_DIR" logs
