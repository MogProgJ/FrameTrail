#!/bin/bash -l
# Queue extra jobs next to the pilot chain without touching it.
# Usage (from $(ws_find frametrail)/rf):  bash training/kit/submit_extra.sh JOB [JOB...]
#   smoke-model  export the GPU smoke test's checkpoint as the app model, to check the app's GPU path early.
#   pilot-model  export the pilot run's best checkpoint (runs/pilot-small) as the app model. Both use EXPORT_OPTS.
#   full-data    build data/full (training/classes/full.txt, the app's whole Open Images vocabulary) in one
#                resumable CPU job, linking the images data/pilot already has instead of downloading them.
#                Settings: FULL_OPTS, FULL_NEED_GB (stops before downloading if the quota is short).
#   full-baseline  score the app's YOLOv8s Open Images model on data/full's test split on CPU: the Phase 2 bar.
#                Settings: FULL_BASELINE_OPTS.
#   full-speed   GPU smoke test of the Phase 2 run on data/full, started from the pilot as the real run is: two
#                short epochs, scoring, measured speed and an export (runs/gpu-smoke-full). Settings: FULL_SPEED_OPTS.
#   full-train   the Phase 2 run: RF-DETR Small on data/full from the pilot (runs/full-small, settings in
#                kit/full-small.env). Waits for full-speed when both are queued together. Settings: FULL_TRAIN_OPTS.
#   report       re-score finished runs from their saved predictions (adds the parent-aware score) and compare each
#                with the YOLOv8s baseline (runs/<run>/compare-baseline.md); CPU only. Settings: REPORT_OPTS.
# Jobs are recorded in logs/extra.txt, never in logs/submitted.txt, so launch/resubmit and the training job's
# clean-up leave them alone. This script never cancels anything, and it does not queue a job again while an
# earlier submission of it is still active. If Slurm refuses a job for a per-user limit, it prints the limits.
set -euo pipefail
source "$(dirname "$0")/env.sh"
JOBS="smoke-model, pilot-model, full-data, full-baseline, full-speed, full-train, report"
[[ $# -gt 0 ]] || { echo "Name at least one job: $JOBS" >&2; exit 2; }
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
    queued_id=$id
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
        smoke-model|pilot-model) check "$job" training/kit/export.sbatch "${EXPORT_OPTS:-}" || valid=0 ;;
        full-data) check full-data training/kit/prepare.sbatch "${FULL_OPTS:-}" || valid=0 ;;
        full-baseline) check full-baseline training/kit/baseline_cpu.sbatch "${FULL_BASELINE_OPTS:-}" || valid=0 ;;
        full-speed) check full-speed training/kit/smoke.sbatch "${FULL_SPEED_OPTS:-}" || valid=0 ;;
        full-train) check full-train training/kit/train.sbatch "${FULL_TRAIN_OPTS:-}" || valid=0 ;;
        report) check report training/kit/report.sbatch "${REPORT_OPTS:-}" || valid=0 ;;
        *) echo "Unknown job '$job'. Jobs: $JOBS" >&2; exit 2 ;;
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
        [[ "$job" != full-speed ]] || speed=$(echo $running | awk '{print $NF}')
        continue
    fi
    case "$job" in
        smoke-model|pilot-model)
            if [[ "$job" == smoke-model ]]; then run=gpu-smoke images=data/pilot-smoke/test name="gpu-smoke test model"
            else run=pilot-small images=data/pilot/test name="RF-DETR Small · Open Images pilot (110 classes)"; fi
            if [[ ! -f "runs/$run/checkpoint_best_total.pth" ]]; then
                echo "$job: runs/$run has no checkpoint; nothing to export." >&2; failed=1; continue
            fi
            if grep -q '"passed": true' "runs/$run/rfdetr_openimages.json" 2>/dev/null; then
                echo "$job: already exported, and its check passed."; continue
            fi
            RUN=$run IMAGES=$images NAME=$name queue "$job" training/kit/export.sbatch "${EXPORT_OPTS:-}" || failed=1
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
        report)
            queue report training/kit/report.sbatch "${REPORT_OPTS:-}" || failed=1
            ;;
        full-speed|full-train)
            if [[ ! -f data/full/dataset.json || ! -f runs/pilot-small/checkpoint_best_total.pth ]]; then
                echo "$job: needs data/full and the pilot's runs/pilot-small/checkpoint_best_total.pth." >&2; failed=1; continue
            fi
            if [[ "$job" == full-speed ]]; then
                if [[ -f runs/gpu-smoke-full/throughput.json ]]; then echo "full-speed: already measured."; speed=done; continue; fi
                DATASET=full SMOKE_RUN=gpu-smoke-full START_FROM=runs/pilot-small/checkpoint_best_total.pth \
                    queue full-speed training/kit/smoke.sbatch "${FULL_SPEED_OPTS:-}" && speed=$queued_id || failed=1
                continue
            fi
            if [[ -f runs/full-small/finished.json && -f runs/full-small/eval-test.json ]]; then
                echo "full-train: runs/full-small is already trained and scored."; continue
            fi
            after=""
            if [[ " $* " == *" full-speed "* ]]; then
                if [[ -z "${speed:-}" ]]; then
                    echo "full-train: not queued, because the full-speed test it should wait for was not queued." >&2
                    failed=1; continue
                fi
                [[ "$speed" == done ]] || after="--dependency=afterok:$speed"
            fi
            DATASET=full MODEL=small RUN=full-small PARTS_NAME=full-train \
                queue full-train training/kit/train.sbatch "$after ${FULL_TRAIN_OPTS:-}" || failed=1
            ;;
    esac
done
echo "Extra jobs recorded in logs/extra.txt:"
cat logs/extra.txt
report
echo "Check with: -Action status"
exit "$failed"
