#!/bin/bash -l
#SBATCH --job-name=frametrail-data-refresh
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --no-requeue
#SBATCH --output=frametrail-data-refresh-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
task_tools="$PWD/output/training-general-v1/data-refresh-2fb87eec-v1"
module load devel/miniforge/25.3.1-python-3.12
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
finish() {
  task_exit=$?
  trap - EXIT
  if ! "$PWD/.venv/bin/python" -B "$task_tools/bundle.py" --root "$PWD" --job "$SLURM_JOB_ID" --exit "$task_exit"; then
    if [[ "$task_exit" -eq 0 ]]; then task_exit=3; fi
  fi
  exit "$task_exit"
}
trap finish EXIT
timeout --signal=TERM --kill-after=20s 2460s srun "$PWD/.venv/bin/python" -u -B "$task_tools/collector.py" --root "$PWD" --job "$SLURM_JOB_ID"
