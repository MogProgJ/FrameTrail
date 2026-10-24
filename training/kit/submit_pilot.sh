#!/bin/bash -l
# Submit the pilot as one chain: prepare data, then (in parallel) train+evaluate and the baseline.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_pilot.sh
set -euo pipefail
source "$(dirname "$0")/env.sh"
mkdir -p logs
export DATASET="${DATASET:-pilot}"
prepare=$(sbatch --parsable --export=ALL training/kit/prepare.sbatch)
train=$(sbatch --parsable --export=ALL --dependency=afterok:$prepare training/kit/train.sbatch)
baseline=$(sbatch --parsable --export=ALL --dependency=afterok:$prepare training/kit/baseline.sbatch)
printf 'prepare %s\ntrain %s\nbaseline %s\n' "$prepare" "$train" "$baseline" | tee -a logs/submitted.txt
echo "Check with: squeue -j $prepare,$train,$baseline"
