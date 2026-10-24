# Shared settings for FrameTrail training on bwUniCluster. Source this; do not run it.
module load devel/miniforge/25.3.1-python-3.12
FT_WS="$(ws_find frametrail)" || { echo "Workspace 'frametrail' not found; see training/README.md" >&2; return 1; }
export FT_ROOT="$FT_WS/rf"
export FT_VENV="$FT_ROOT/.venv"
export RF_HOME="$FT_ROOT/.cache/rfdetr"   # Official RF-DETR weights
export HF_HOME="$FT_ROOT/.cache/huggingface"
export TORCH_HOME="$FT_ROOT/.cache/torch"
export PIP_CACHE_DIR="$FT_ROOT/.cache/pip"
export YOLO_CONFIG_DIR="$FT_ROOT/.cache/ultralytics"
export PYTHONUNBUFFERED=1
cd "$FT_ROOT" || { echo "Copy the training folder to $FT_ROOT first" >&2; return 1; }
