#!/bin/bash -l
#SBATCH --job-name=frametrail-rf-billboard-batch
#SBATCH --partition=gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --gres=gpu:1
#SBATCH --array=0-3%2
#SBATCH --no-requeue
#SBATCH --time=00:45:00
#SBATCH --output=frametrail-rf-billboard-batch-%A_%a.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
[[ "$SLURM_ARRAY_JOB_ID" =~ ^[0-9]+$ && "$SLURM_ARRAY_TASK_ID" =~ ^[0-3]$ && "$SLURM_ARRAY_TASK_COUNT" == 4 ]] || exit 65
task_tools="$PWD/output/training-general-v1/rf-billboard-batch-0a255598-v1"
task_run_id="${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
export PYTHONPATH="$PWD/output/rf-comparison-v1/python-overlay"
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
module load devel/miniforge/25.3.1-python-3.12
task_training_exit=77
task_post_exit=77
finish() {
  task_exit=$?
  trap - EXIT
  if ! "$PWD/.venv/bin/python" -B "$task_tools/bundle_results.py" --project "$PWD" --job "$task_run_id" --exit-code "$task_exit" --training-exit "$task_training_exit" --post-exit "$task_post_exit"; then
    echo 'Archive failed; preserve task output and log.'
    if [[ "$task_exit" -eq 0 ]]; then task_exit=3; fi
  fi
  exit "$task_exit"
}
trap finish EXIT
"$PWD/.venv/bin/python" -B "$task_tools/verify_package.py"
set +e
timeout --signal=TERM --kill-after=30s 1800s srun "$PWD/.venv/bin/python" -u -B "$task_tools/train_balanced.py"
task_training_exit=$?
set -e
[[ "$task_training_exit" -eq 0 ]] || exit "$task_training_exit"
set +e
timeout --signal=TERM --kill-after=30s 480s srun "$PWD/.venv/bin/python" -u -B "$task_tools/regression_stage.py" --project "$PWD"
task_post_exit=$?
set -e
exit "$task_post_exit"
