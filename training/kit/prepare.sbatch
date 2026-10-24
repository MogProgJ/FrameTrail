#!/bin/bash -l
#SBATCH --job-name=ft-prepare
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x-%j.log
# Build data/$DATASET from Open Images (metadata ~6 GB, pilot images ~20 GB). Re-running resumes downloads.
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-pilot}"
"$FT_VENV/bin/python" training/openimages.py --classes "training/classes/$DATASET.txt" \
    --out "data/$DATASET" --cache data/openimages-metadata --workers 64 ${PREPARE_ARGS:-}
