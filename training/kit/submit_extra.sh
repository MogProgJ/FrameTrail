#!/bin/bash -l
# Queue extra jobs next to the pilot chain without touching it.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_extra.sh JOB [JOB...]
#   smoke-model  export the GPU smoke test's checkpoint as the app model, to check the app's GPU path early.
#                Settings: EXPORT_OPTS, EXPORT_FALLBACK_OPTS.
#   full-data    build data/full (training/classes/full.txt, the app's whole Open Images vocabulary) in one
#                resumable CPU job, linking the images data/pilot already has instead of downloading them.
#                Settings: FULL_OPTS, FULL_FALLBACK_OPTS, FULL_NEED_GB (stops before downloading if the quota is short).
# A job the queue refuses (e.g. the dev queues' per-user limit, which the account shares with its other
# project) is tried once more with its *_FALLBACK_OPTS. Jobs are recorded in logs/extra.txt, never in
# logs/submitted.txt, so launch/resubmit and the training job's clean-up leave them alone. This script never
# cancels anything, and it does not queue a job again while an earlier submission of it is still active.
set -euo pipefail
source "$(dirname "$0")/env.sh"
[[ $# -gt 0 ]] || { echo "Name at least one job: smoke-model, full-data" >&2; exit 2; }
touch logs/extra.txt

active() {  # Recorded IDs of job $1 that are still queued or running.
    local ids
    ids=$(awk -v name="$1" '$1 == name {print $2}' logs/extra.txt | paste -sd,)
    [[ -z "$ids" ]] || squeue -h -j "$ids" -o %i 2>/dev/null || true
}
check() {  # check SCRIPT [OPTIONS...]: Slurm validates the request; nothing is queued.
    local script="$1" reply; shift
    reply=$(sbatch --test-only "$@" "$script" 2>&1) || { echo "$reply" >&2; return 1; }
}
queue() {  # queue NAME SCRIPT OPTIONS FALLBACK: submit with OPTIONS, else with FALLBACK; record the ID.
    local name="$1" script="$2" options="$3" fallback="$4" id reply
    if reply=$(sbatch --parsable --export=ALL $options "$script" 2>&1); then
        id=$reply
    elif [[ -n "$fallback" ]] && echo "$reply" | grep -q -i 'limit\|policy'; then
        echo "$name: the queue refused it (${reply##*error: }); trying $fallback instead."
        reply=$(sbatch --parsable --export=ALL $fallback "$script" 2>&1) || { echo "$name: not queued: $reply" >&2; return 1; }
        id=$reply
    else
        echo "$name: not queued: $reply" >&2
        return 1
    fi
    echo "$name $id" >> logs/extra.txt
    echo "$name: queued as job $id"
}

# Validate every request (and its fallback) before anything is queued.
for job in "$@"; do
    case "$job" in
        smoke-model) check training/kit/export.sbatch ${EXPORT_OPTS:-}
                     [[ -z "${EXPORT_FALLBACK_OPTS:-}" ]] || check training/kit/export.sbatch $EXPORT_FALLBACK_OPTS ;;
        full-data) check training/kit/prepare.sbatch ${FULL_OPTS:-}
                   [[ -z "${FULL_FALLBACK_OPTS:-}" ]] || check training/kit/prepare.sbatch $FULL_FALLBACK_OPTS ;;
        *) echo "Unknown job '$job'. Jobs: smoke-model, full-data" >&2; exit 2 ;;
    esac
done
echo "Slurm accepted the requests; queuing."

failed=0
for job in "$@"; do
    running=$(active "$job")
    if [[ -n "$running" ]]; then
        echo "$job: already queued or running ($(echo $running)); not queued again."
        continue
    fi
    case "$job" in
        smoke-model)
            if [[ ! -f runs/gpu-smoke/checkpoint_best_total.pth ]]; then
                echo "smoke-model: runs/gpu-smoke has no checkpoint; nothing to export." >&2; failed=1; continue
            fi
            if [[ -f runs/gpu-smoke/rfdetr_openimages.onnx ]]; then echo "smoke-model: already exported."; continue; fi
            RUN=gpu-smoke queue smoke-model training/kit/export.sbatch "${EXPORT_OPTS:-}" "${EXPORT_FALLBACK_OPTS:-}" || failed=1
            ;;
        full-data)
            if [[ -f data/full/dataset.json ]]; then echo "full-data: data/full is already built."; continue; fi
            DATASET=full PREPARE_ARGS="--reuse data/pilot" NEED_GB="${FULL_NEED_GB:-}" \
                queue full-data training/kit/prepare.sbatch "${FULL_OPTS:-}" "${FULL_FALLBACK_OPTS:-}" || failed=1
            ;;
    esac
done
echo "Extra jobs recorded in logs/extra.txt:"
cat logs/extra.txt
echo "Check with: -Action status"
exit "$failed"
