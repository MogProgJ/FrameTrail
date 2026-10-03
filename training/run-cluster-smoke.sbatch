#!/bin/bash -l
# One development job to verify the existing 96-image training bundle on KIT.
# CPU/memory defaults follow the GPU partition policy; account/queue may be overridden.
#SBATCH --job-name=frametrail-smoke
#SBATCH --partition=dev_gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --time=00:15:00
#SBATCH --output=frametrail-smoke-%j.log
set -euo pipefail
module load devel/miniforge/25.3.1-python-3.12
: "${SLURM_JOB_ID:?Submit with sbatch rather than running on a login node}"
: "${SLURM_SUBMIT_DIR:?Submit from the uploaded FrameTrail folder}"
FT_ROOT="${FT_ROOT:-$SLURM_SUBMIT_DIR}"
cd "$FT_ROOT"
FT_PYTHON="$FT_ROOT/.venv/bin/python"
FT_DATASET="$FT_ROOT/output/training-0.13/general-smoke-bundle"
FT_WEIGHTS="$FT_ROOT/.deps/world-export/weights/yolov8s-oiv7.pt"
FT_OUTPUT="$FT_ROOT/output/cluster-smoke-$SLURM_JOB_ID"
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
test -x "$FT_PYTHON"
srun "$FT_PYTHON" -c 'import torch; assert torch.__version__.split("+")[0] == "2.8.0"; assert torch.cuda.is_available(), "CUDA GPU unavailable"; print("Training GPU:", torch.cuda.get_device_name(0)); print("CUDA runtime:", torch.version.cuda); print("GPU tensor check:", torch.ones(8, device="cuda").sum().item())'
srun "$FT_PYTHON" -B scripts/train-detector.py --dataset "$FT_DATASET" \
  --config training/general-cluster-smoke.json --weights "$FT_WEIGHTS" --mode smoke
srun "$FT_PYTHON" -B scripts/train-detector.py --dataset "$FT_DATASET" \
  --config training/general-cluster-smoke.json --weights "$FT_WEIGHTS" \
  --output "$FT_OUTPUT" --mode smoke --run
printf 'Completed mechanical training check. Results: %s\n' "$FT_OUTPUT"
