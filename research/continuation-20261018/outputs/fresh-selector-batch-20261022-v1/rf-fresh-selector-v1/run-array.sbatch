#!/bin/bash
#SBATCH --job-name=frametrail-fresh-selector
#SBATCH --partition=gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --gres=gpu:1
#SBATCH --array=0-1%2
#SBATCH --time=00:45:00
#SBATCH --no-requeue
set -euo pipefail
task_tools="$1"
task_project="$SLURM_SUBMIT_DIR"
task_python="$task_project/.venv/bin/python"
module load devel/miniforge/25.3.1-python-3.12
export PYTHONPATH="$task_project/output/rf-comparison-v1/python-overlay"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
task_finalize() {
  task_exit=$?
  trap - EXIT
  timeout --signal=TERM --kill-after=20s 480s "$task_python" -B "$task_tools/bundle_results.py" --project "$task_project" --exit-code "$task_exit" || exit 70
  exit "$task_exit"
}
trap task_finalize EXIT
timeout --signal=TERM --kill-after=30s 1800s srun "$task_python" -u -B "$task_tools/train.py" --project "$task_project"
