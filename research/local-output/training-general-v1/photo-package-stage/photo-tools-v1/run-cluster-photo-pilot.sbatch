#!/bin/bash -l
# First 60 frozen intake IDs only. No GPU, training, export or review approval.
#SBATCH --job-name=frametrail-photos
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --output=frametrail-photos-%j.log
set -euo pipefail
module load devel/miniforge/25.3.1-python-3.12
: "${SLURM_JOB_ID:?Submit through sbatch}"
: "${SLURM_SUBMIT_DIR:?Submit from the FrameTrail project}"
: "${FT_SELECTION_JOB:?Set the verified v2 selection job ID}"
[[ "$FT_SELECTION_JOB" =~ ^[0-9]+$ ]]
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'Photo acquisition job: %s\nSelection job: %s\n' "$SLURM_JOB_ID" "$FT_SELECTION_JOB"
srun "$SLURM_SUBMIT_DIR/.venv/bin/python" -B \
  output/training-general-v1/photo-tools-v1/acquire-pilot-images.py \
  --root "$SLURM_SUBMIT_DIR" --selection-job "$FT_SELECTION_JOB" \
  --job-id "$SLURM_JOB_ID" --run
printf 'Photo job report: output/training-general-v1/photo-job-%s/acquisition.json\n' "$SLURM_JOB_ID"
