#!/bin/bash -l
# Submit the pilot as one chain: prepare data, then (in parallel) train+evaluate and the baseline.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_pilot.sh
#
# Optional settings (environment variables):
#   TRAIN_PARTS=6 TRAIN_OPTS="--time=04:00:00"   split training into 6 back-to-back 4-hour jobs;
#                                                 shorter jobs usually start sooner, and each resumes.
#   PREPARE_OPTS / BASELINE_OPTS                  extra sbatch options, e.g. "--cpus-per-task=4 --time=03:00:00"
# The data job is skipped when data/$DATASET/dataset.json already exists.
# Refuses to submit while jobs from an earlier submission are still queued or running.
set -euo pipefail
source "$(dirname "$0")/env.sh"
export DATASET="${DATASET:-pilot}"
TRAIN_PARTS="${TRAIN_PARTS:-1}"

if [[ -s logs/submitted.txt ]]; then
    previous=$(awk '{print $2}' logs/submitted.txt | paste -sd,)
    active=$(squeue -h -j "$previous" -o %i 2>/dev/null || true)
    if [[ -n "$active" ]]; then
        echo "Earlier FrameTrail jobs are still active: $(echo $active)" >&2
        echo "Not submitting again. Cancel them first with: scancel $(echo $active)" >&2
        exit 1
    fi
fi

# Ask Slurm to validate every request before anything is queued.
sbatch --test-only ${PREPARE_OPTS:-} training/kit/prepare.sbatch >/dev/null
sbatch --test-only ${TRAIN_OPTS:-} training/kit/train.sbatch >/dev/null
sbatch --test-only ${BASELINE_OPTS:-} training/kit/baseline.sbatch >/dev/null

: > logs/submitted.txt.new
after=""
if [[ -f "data/$DATASET/dataset.json" ]]; then
    echo "data/$DATASET is already built; skipping the data job."
else
    prepare=$(sbatch --parsable --export=ALL ${PREPARE_OPTS:-} training/kit/prepare.sbatch)
    echo "prepare $prepare" >> logs/submitted.txt.new
    after="--dependency=afterok:$prepare"
fi
baseline=$(sbatch --parsable --export=ALL $after ${BASELINE_OPTS:-} training/kit/baseline.sbatch)
echo "baseline $baseline" >> logs/submitted.txt.new
for part in $(seq 1 "$TRAIN_PARTS"); do
    train=$(sbatch --parsable --export=ALL $after ${TRAIN_OPTS:-} training/kit/train.sbatch)
    echo "train $train" >> logs/submitted.txt.new
    # Later parts start whether the previous part finished or hit its time limit; each resumes.
    after="--dependency=afterany:$train"
done
mv logs/submitted.txt.new logs/submitted.txt
cat logs/submitted.txt
echo "Check with: squeue -j $(awk '{print $2}' logs/submitted.txt | paste -sd,)"
