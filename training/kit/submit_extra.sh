#!/bin/bash -l
# Queue extra jobs next to the pilot chain without touching it.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_extra.sh JOB [JOB...]
#   smoke-model  export the GPU smoke test's checkpoint as the app model, to check the app's GPU path early.
#                Settings: EXPORT_OPTS.
#   full-data    build data/full (training/classes/full.txt, the app's whole Open Images vocabulary) in one
#                resumable CPU job, linking the images data/pilot already has instead of downloading them.
#                Settings: FULL_OPTS, FULL_NEED_GB (stops before downloading if the quota is short).
#   full-baseline  score the app's YOLOv8s Open Images model on data/full's test split on CPU: the Phase 2 bar.
#                Settings: FULL_BASELINE_OPTS.
# Jobs are recorded in logs/extra.txt, never in logs/submitted.txt, so launch/resubmit and the training job's
# clean-up leave them alone. This script never cancels anything, and it does not queue a job again while an
# earlier submission of it is still active. If Slurm refuses a job for a per-user limit, it prints the limits.
set -euo pipefail
source "$(dirname "$0")/env.sh"
[[ $# -gt 0 ]] || { echo "Name at least one job: smoke-model, full-data, full-baseline" >&2; exit 2; }
touch logs/extra.txt
refused=0

active() {  # Recorded IDs of job $1 that are still queued or running.
    local ids
    ids=$(awk -v name="$1" '$1 == name {print $2}' logs/extra.txt | paste -sd,)
    [[ -z "$ids" ]] || squeue -h -j "$ids" -o %i 2>/dev/null || true
}
refusal() {  # refusal NAME REPLY: report why Slurm refused; note per-user limits for the report.
    echo "$1: Slurm refused it: $2" >&2
    if echo "$2" | grep -q -i 'limit\|policy'; then refused=1; fi
}
check() {  # check NAME SCRIPT OPTIONS: Slurm validates the request; nothing is queued.
    local reply
    reply=$(sbatch --test-only $3 "$2" 2>&1) || { refusal "$1" "$reply"; return 1; }
}
queue() {  # queue NAME SCRIPT OPTIONS: submit and record the job ID.
    local id
    id=$(sbatch --parsable --export=ALL $3 "$2" 2>&1) || { refusal "$1" "$id"; return 1; }
    echo "$1 $id" >> logs/extra.txt
    echo "$1: queued as job $id"
}
report() {  # Read-only: FrameTrail's own job count and the per-user limits. Other jobs are not listed.
    [[ "$refused" == 1 ]] || return 0
    local ids own partition
    ids=$(cat logs/submitted.txt logs/extra.txt 2>/dev/null | awk '{print $2}' | paste -sd,)
    own=$( [[ -z "$ids" ]] || squeue -h -j "$ids" -o %i 2>/dev/null | wc -l || true)
    echo
    echo "A per-user job limit is full. FrameTrail itself has ${own:-0} queued or running job(s); the rest of"
    echo "the limit is used by other work under this user account. Nothing was cancelled. Try again once it frees up."
    for partition in dev_cpu_il cpu_il; do
        echo "  $partition: $(scontrol show partition "$partition" 2>/dev/null | grep -o 'QoS=[^ ]*' || echo 'QoS unknown')"
    done
    echo "Per-user limits of the quality-of-service levels that have one (MaxSubmitPU = queued + running jobs):"
    sacctmgr -n -P show qos format=Name,MaxSubmitPU,MaxJobsPU 2>/dev/null \
        | awk -F'|' '$2 != "" || $3 != "" {printf "  %-20s MaxSubmitPU=%-6s MaxJobsPU=%s\n", $1, $2, $3}' || true
}

# Validate every request before anything is queued.
valid=1
for job in "$@"; do
    case "$job" in
        smoke-model) check smoke-model training/kit/export.sbatch "${EXPORT_OPTS:-}" || valid=0 ;;
        full-data) check full-data training/kit/prepare.sbatch "${FULL_OPTS:-}" || valid=0 ;;
        full-baseline) check full-baseline training/kit/baseline_cpu.sbatch "${FULL_BASELINE_OPTS:-}" || valid=0 ;;
        *) echo "Unknown job '$job'. Jobs: smoke-model, full-data, full-baseline" >&2; exit 2 ;;
    esac
done
if [[ "$valid" == 0 ]]; then
    echo "Nothing was queued."
    report
    exit 1
fi
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
            RUN=gpu-smoke queue smoke-model training/kit/export.sbatch "${EXPORT_OPTS:-}" || failed=1
            ;;
        full-data)
            if [[ -f data/full/dataset.json ]]; then echo "full-data: data/full is already built."; continue; fi
            DATASET=full PREPARE_ARGS="--reuse data/pilot" NEED_GB="${FULL_NEED_GB:-}" \
                queue full-data training/kit/prepare.sbatch "${FULL_OPTS:-}" || failed=1
            ;;
        full-baseline)
            if [[ ! -f data/full/dataset.json ]]; then echo "full-baseline: data/full is not built yet." >&2; failed=1; continue; fi
            if [[ -f runs/baseline-yolov8s-oiv7-full/eval-test.json ]]; then echo "full-baseline: already scored."; continue; fi
            DATASET=full queue full-baseline training/kit/baseline_cpu.sbatch "${FULL_BASELINE_OPTS:-}" || failed=1
            ;;
    esac
done
echo "Extra jobs recorded in logs/extra.txt:"
cat logs/extra.txt
report
echo "Check with: -Action status"
exit "$failed"
