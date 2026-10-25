#!/bin/bash -l
# Queue extra jobs next to the pilot chain without touching it.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_extra.sh JOB [JOB...]
#   full-data    build data/full (training/classes/full.txt, the app's whole Open Images vocabulary) in
#                resumable CPU parts, linking the images data/pilot already has instead of downloading them.
#                Settings: FULL_PARTS, FULL_OPTS, FULL_NEED_GB (stops before downloading if the quota is short).
#   smoke-model  export the GPU smoke test's checkpoint as the app model, to check the app's GPU path early.
#                Settings: EXPORT_OPTS.
# Jobs are recorded in logs/extra.txt, never in logs/submitted.txt, so launch/resubmit and the training job's
# clean-up leave them alone. This script never cancels anything, and it does not queue a job again while an
# earlier submission of it is still queued or running.
set -euo pipefail
source "$(dirname "$0")/env.sh"
[[ $# -gt 0 ]] || { echo "Name at least one job: full-data, smoke-model" >&2; exit 2; }
touch logs/extra.txt

active() {  # Recorded IDs of job $1 that are still queued or running.
    local ids
    ids=$(awk -v name="$1" '$1 == name {print $2}' logs/extra.txt | paste -sd,)
    [[ -z "$ids" ]] || squeue -h -j "$ids" -o %i 2>/dev/null || true
}

# Ask Slurm to validate every request before anything is queued.
for job in "$@"; do
    case "$job" in
        full-data) sbatch --test-only ${FULL_OPTS:-} training/kit/prepare.sbatch >/dev/null ;;
        smoke-model) sbatch --test-only ${EXPORT_OPTS:-} training/kit/export.sbatch >/dev/null ;;
        *) echo "Unknown job '$job'. Jobs: full-data, smoke-model" >&2; exit 2 ;;
    esac
done

for job in "$@"; do
    running=$(active "$job")
    if [[ -n "$running" ]]; then
        echo "$job is already queued or running: $(echo $running). Not submitting it again."
        continue
    fi
    case "$job" in
        full-data)
            if [[ -f data/full/dataset.json ]]; then echo "data/full is already built."; continue; fi
            after=""
            for part in $(seq 1 "${FULL_PARTS:-4}"); do
                # Queues may cap jobs per user: keep the parts that were accepted.
                if id=$(DATASET=full PREPARE_ARGS="--reuse data/pilot" NEED_GB="${FULL_NEED_GB:-}" \
                        sbatch --parsable --export=ALL ${after:+--dependency=afterany:$after} ${FULL_OPTS:-} \
                        training/kit/prepare.sbatch); then
                    echo "full-data $id" >> logs/extra.txt
                    after=$id
                else
                    [[ -n "$after" ]] || exit 1
                    echo "Data part $part was not accepted; continuing with $((part - 1)) part(s)." >&2
                    break
                fi
            done
            ;;
        smoke-model)
            if [[ ! -f runs/gpu-smoke/checkpoint_best_total.pth ]]; then
                echo "runs/gpu-smoke has no checkpoint; nothing to export." >&2; exit 1
            fi
            if [[ -f runs/gpu-smoke/rfdetr_openimages.onnx ]]; then echo "The smoke-test model is already exported."; continue; fi
            id=$(RUN=gpu-smoke sbatch --parsable --export=ALL ${EXPORT_OPTS:-} training/kit/export.sbatch)
            echo "smoke-model $id" >> logs/extra.txt
            ;;
    esac
done
echo "Extra jobs recorded in logs/extra.txt:"
cat logs/extra.txt
echo "Check with: -Action status"
