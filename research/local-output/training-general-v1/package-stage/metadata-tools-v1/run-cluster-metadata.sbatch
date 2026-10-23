#!/bin/bash -l
# Acquire bounded train metadata and inventory; no photographs, GPU or training.
#SBATCH --job-name=frametrail-metadata
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=frametrail-metadata-%j.log
set -euo pipefail
module load devel/miniforge/25.3.1-python-3.12
: "${SLURM_JOB_ID:?Submit through sbatch}"
: "${SLURM_SUBMIT_DIR:?Submit from the existing FrameTrail project}"
FT_ROOT="$SLURM_SUBMIT_DIR"
FT_TOOLS="$FT_ROOT/output/training-general-v1/metadata-tools-v1"
FT_PYTHON="$FT_ROOT/.venv/bin/python"
FT_METADATA="$FT_ROOT/output/training-general-v1/source-metadata"
FT_OUTPUT="$FT_ROOT/output/training-general-v1/catalogue-$SLURM_JOB_ID"
cd "$FT_ROOT"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
test -x "$FT_PYTHON"
test -f "$FT_TOOLS/acquire-cluster-metadata.py"
printf 'Metadata preparation job: %s\nHost: %s\nOutput: %s\n' "$SLURM_JOB_ID" "$(hostname)" "$FT_OUTPUT"
srun "$FT_PYTHON" -B "$FT_TOOLS/acquire-cluster-metadata.py" \
  --root "$FT_ROOT" --inputs "$FT_TOOLS" --metadata "$FT_METADATA" --output "$FT_OUTPUT"
srun "$FT_PYTHON" -B "$FT_TOOLS/acquire-cluster-metadata.py" \
  --root "$FT_ROOT" --inputs "$FT_TOOLS" --metadata "$FT_METADATA" --output "$FT_OUTPUT" --run
printf 'Completed metadata catalogue. Results: %s\n' "$FT_OUTPUT"
