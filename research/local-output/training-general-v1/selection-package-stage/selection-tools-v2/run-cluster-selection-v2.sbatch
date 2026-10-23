#!/bin/bash -l
# All-anchor metadata-only revision; reuse completed catalogue and environment.
#SBATCH --job-name=frametrail-selection-v2
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=frametrail-selection-v2-%j.log
set -euo pipefail
module load devel/miniforge/25.3.1-python-3.12
: "${SLURM_JOB_ID:?Submit through sbatch}"
: "${SLURM_SUBMIT_DIR:?Submit from the existing FrameTrail project}"
: "${FT_CATALOGUE_JOB:?Set the completed catalogue job ID}"
: "${FT_PRIOR_SELECTION_JOB:?Set the verified original selection job ID}"
[[ "$FT_CATALOGUE_JOB" =~ ^[0-9]+$ ]]
[[ "$FT_PRIOR_SELECTION_JOB" =~ ^[0-9]+$ ]]
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
printf 'Selection v2 job: %s\nCatalogue job: %s\nPrior selection job: %s\n' "$SLURM_JOB_ID" "$FT_CATALOGUE_JOB" "$FT_PRIOR_SELECTION_JOB"
srun "$SLURM_SUBMIT_DIR/.venv/bin/python" -B \
  output/training-general-v1/selection-tools-v2/select-balanced-pilot.py \
  --root "$SLURM_SUBMIT_DIR" --catalogue-job "$FT_CATALOGUE_JOB" \
  --prior-selection-job "$FT_PRIOR_SELECTION_JOB" --job-id "$SLURM_JOB_ID" \
  --expected-prior-sha256 f09990778704c7e51d54295fa88e0b39da0a840f77cc7fa6de01a06e16869d15 \
  --run
printf 'Completed selection v2. Results: output/training-general-v1/pilot-selection-v2-%s\n' "$SLURM_JOB_ID"
