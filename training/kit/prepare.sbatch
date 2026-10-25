#!/bin/bash -l
#SBATCH --job-name=ft-prepare
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x-%j.log
# Build data/$DATASET from Open Images (metadata ~6 GB, pilot images ~16 GB). Re-running resumes downloads,
# so the job can be split into several short parts (PREPARE_PARTS in submit_pilot.sh, FULL_PARTS in
# submit_extra.sh). PREPARE_ARGS adds builder options, e.g. --reuse data/pilot.
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-pilot}"
if [[ -f "data/$DATASET/dataset.json" ]]; then
    echo "data/$DATASET is already complete."
    exit 0
fi
# NEED_GB: estimated size of the images still to download; stop early if the quota cannot hold them.
[[ -z "${NEED_GB:-}" ]] || bash training/kit/space_check.sh "$NEED_GB"
"$FT_VENV/bin/python" training/openimages.py --classes "training/classes/$DATASET.txt" \
    --out "data/$DATASET" --cache data/openimages-metadata --workers 64 ${PREPARE_ARGS:-}
