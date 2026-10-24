#!/bin/bash -l
# Submit the pilot chain:
#   data (PREPARE_PARTS short parts that resume) -> GPU smoke test + baseline -> long training (+ scoring)
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_pilot.sh
#
# Settings (environment variables, normally from training/kit/submit.env):
#   PREPARE_PARTS / PREPARE_OPTS   number of data parts and extra sbatch options for them
#   SMOKE=1 / SMOKE_OPTS           run the GPU smoke test; training then only starts if it passed
#   TRAIN_PARTS / TRAIN_OPTS       training jobs (each resumes) and extra sbatch options
#   BASELINE_OPTS                  extra sbatch options for the baseline scoring
#   CHECK_ONLY=1                   only let Slurm validate the requests (sbatch --test-only), submit nothing
# The data job is skipped when data/$DATASET/dataset.json already exists.
# Refuses to submit while jobs from an earlier submission are still queued or running.
set -euo pipefail
source "$(dirname "$0")/env.sh"
export DATASET="${DATASET:-pilot}"
PREPARE_PARTS="${PREPARE_PARTS:-1}"
TRAIN_PARTS="${TRAIN_PARTS:-1}"
SMOKE="${SMOKE:-0}"

# Ask Slurm to validate every request before anything is queued.
sbatch --test-only ${PREPARE_OPTS:-} training/kit/prepare.sbatch >/dev/null
sbatch --test-only ${TRAIN_OPTS:-} training/kit/train.sbatch >/dev/null
sbatch --test-only ${BASELINE_OPTS:-} training/kit/baseline.sbatch >/dev/null
[[ "$SMOKE" == 1 ]] && sbatch --test-only ${SMOKE_OPTS:-} training/kit/smoke.sbatch >/dev/null
if [[ "${CHECK_ONLY:-0}" == 1 ]]; then
    echo "All requests are valid."
    exit 0
fi

if [[ -s logs/submitted.txt ]]; then
    previous=$(awk '{print $2}' logs/submitted.txt | paste -sd,)
    active=$(squeue -h -j "$previous" -o %i 2>/dev/null || true)
    if [[ -n "$active" ]]; then
        echo "Earlier FrameTrail jobs are still active: $(echo $active)" >&2
        echo "Not submitting again. Use -Action resubmit to replace them." >&2
        exit 1
    fi
fi

: > logs/submitted.txt.new
# Record every job that was queued, even if a later submission fails.
trap 'mv -f logs/submitted.txt.new logs/submitted.txt; cat logs/submitted.txt' EXIT
data=""
if [[ -f "data/$DATASET/dataset.json" ]]; then
    echo "data/$DATASET is already built; skipping the data job."
else
    for part in $(seq 1 "$PREPARE_PARTS"); do
        # Queues may cap jobs per user: keep the parts that were accepted and continue.
        if next=$(sbatch --parsable --export=ALL ${data:+--dependency=afterany:$prepare} ${PREPARE_OPTS:-} \
                training/kit/prepare.sbatch); then
            prepare=$next
            echo "prepare $prepare" >> logs/submitted.txt.new
            data=1
        else
            [[ -n "$data" ]] || exit 1
            echo "Data part $part was not accepted; continuing with $((part - 1)) part(s)." >&2
            break
        fi
    done
fi
# Everything else needs the finished data: the last data part must succeed.
after=${data:+--dependency=afterok:$prepare}
if baseline=$(sbatch --parsable --export=ALL $after ${BASELINE_OPTS:-} training/kit/baseline.sbatch); then
    echo "baseline $baseline" >> logs/submitted.txt.new
else
    echo "The baseline job was not accepted; submit it later on its own." >&2
fi
if [[ "$SMOKE" == 1 ]]; then
    if smoke=$(sbatch --parsable --export=ALL $after ${SMOKE_OPTS:-} training/kit/smoke.sbatch); then
        echo "smoke $smoke" >> logs/submitted.txt.new
        after="--dependency=afterok:$smoke"
    else
        echo "The GPU smoke test was not accepted; training will not wait for it." >&2
    fi
fi
for part in $(seq 1 "$TRAIN_PARTS"); do
    train=$(sbatch --parsable --export=ALL $after ${TRAIN_OPTS:-} training/kit/train.sbatch)
    echo "train $train" >> logs/submitted.txt.new
    # Later parts start whether the previous part finished or hit its time limit; each resumes.
    after="--dependency=afterany:$train"
done
echo "Check with: -Action status"
