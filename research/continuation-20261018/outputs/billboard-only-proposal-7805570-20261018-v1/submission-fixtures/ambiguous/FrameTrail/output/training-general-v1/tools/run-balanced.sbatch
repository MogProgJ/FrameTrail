#!/bin/bash -l
#SBATCH --job-name=frametrail-rf-billboard
#SBATCH --partition=gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=gpu:1
#SBATCH --time=00:45:00
#SBATCH --output=frametrail-rf-billboard-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
task_tools="$PWD/output/training-general-v1/rf-billboard-ddbb57c6-v1"
export PYTHONPATH="$PWD/output/rf-comparison-v1/python-overlay"
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
module load devel/miniforge/25.3.1-python-3.12
finish() {
  task_exit=$?
  trap - EXIT
  if ! "$PWD/.venv/bin/python" -B "$task_tools/bundle_results.py" --project "$PWD" --job "$SLURM_JOB_ID" --exit-code "$task_exit"; then
    echo 'Archive failed; preserve output and log.'
    if [[ "$task_exit" -eq 0 ]]; then task_exit=3; fi
  fi
  exit "$task_exit"
}
trap finish EXIT
"$PWD/.venv/bin/python" -B "$task_tools/verify_package.py"
timeout --signal=TERM --kill-after=30s 1800s srun "$PWD/.venv/bin/python" -u -B "$task_tools/train_balanced.py"
