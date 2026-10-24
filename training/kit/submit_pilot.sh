#!/bin/bash -l
# Submit the pilot as one chain: prepare data, then (in parallel) train+evaluate and the baseline.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_pilot.sh
# Refuses to submit while jobs from an earlier submission are still queued or running.
set -euo pipefail
source "$(dirname "$0")/env.sh"
mkdir -p logs
export DATASET="${DATASET:-pilot}"

if [[ -s logs/submitted.txt ]]; then
    previous=$(awk '{print $2}' logs/submitted.txt | paste -sd,)
    active=$(squeue -h -j "$previous" -o %i 2>/dev/null || true)
    if [[ -n "$active" ]]; then
        echo "Earlier FrameTrail jobs are still active: $(echo $active)" >&2
        echo "Not submitting again. Check with: squeue -j $previous" >&2
        exit 1
    fi
fi

# Ask Slurm to validate every request before anything is queued.
for job in prepare train baseline; do
    sbatch --test-only training/kit/$job.sbatch >/dev/null
done

prepare=$(sbatch --parsable --export=ALL training/kit/prepare.sbatch)
train=$(sbatch --parsable --export=ALL --dependency=afterok:$prepare training/kit/train.sbatch)
baseline=$(sbatch --parsable --export=ALL --dependency=afterok:$prepare training/kit/baseline.sbatch)
printf 'prepare %s\ntrain %s\nbaseline %s\n' "$prepare" "$train" "$baseline" > logs/submitted.txt
cat logs/submitted.txt
echo "Check with: squeue -j $prepare,$train,$baseline"
