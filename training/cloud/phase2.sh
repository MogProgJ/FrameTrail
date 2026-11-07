#!/bin/bash
# Phase 2 on ONE rented Linux machine with an NVIDIA GPU (an Azure NC-series VM, RunPod, Lambda, ...): no Slurm.
# Every stage skips what is already done, so after an interruption (spot eviction, SSH drop) run it again and it
# carries on; training resumes from its last checkpoint. Run it inside tmux or `nohup`, so it survives a closed laptop.
#
#   git clone <repo> && cd FrameTrail          (or copy the repository)
#   bash training/cloud/phase2.sh              all stages
#   bash training/cloud/phase2.sh data         one or more named stages: setup data baseline train report
#
# Where: $FT_ROOT (default ~/frametrail-work) holds .venv, data/, runs/, weights/. Needs about 150 GB of disk, a GPU
# with 40 GB or more, and python3.12 or newer with venv. Environment variables:
#   PRICE_PER_HOUR       what this machine costs per hour in dollars, e.g. 0.69 (needed by the plan stage)
#   BUDGET_USD           what you are willing to spend on training, e.g. 25 (default 25)
#   TRAIN_CAP            images per class for the training set (default 300: 102,598 training images, about 35 GB; 600 gives
#                        175,051 images, 60 GB; 200 gives 72,660). The test split is the same for every cap.
#   RUN_DEATH_SWITCH=1   power the machine off when the script ends or fails (stops the per-hour billing; it does not
#                        delete the disk). Leave unset to keep it on.
#   TRAIN_ARGS           extra train.py options, e.g. "--unverified-weight 0.25"
# Settings (epochs, batch size, run to start from) are in training/kit/full-small.env, as on the cluster.
set -euo pipefail
cd "$(dirname "$0")/../.."
STAGES=("$@"); [[ ${#STAGES[@]} -gt 0 ]] || STAGES=(setup data baseline plan train report package)
log() { printf '\n=== %s  %s\n' "$(date '+%F %T')" "$*"; }
want() { [[ " ${STAGES[*]} " == *" $1 "* ]]; }

if [[ "${RUN_DEATH_SWITCH:-0}" == 1 ]]; then
    trap 'log "Finished or failed; powering off (RUN_DEATH_SWITCH=1)"; sync; sudo poweroff' EXIT
fi
if [[ "${ALLOW_NO_GPU:-0}" != 1 ]]; then   # kaggle_round3.sh sets it for a CPU-only session (data and teacher stages only)
    command -v nvidia-smi >/dev/null || { echo "No NVIDIA GPU driver found (nvidia-smi missing)." >&2; exit 1; }
    nvidia-smi --query-gpu=name,memory.total --format=csv
fi

# The repository's scripts expect to run from $FT_ROOT with training/ inside it.
REPO="$PWD"
export FT_ROOT="${FT_ROOT:-$HOME/frametrail-work}"
mkdir -p "$FT_ROOT"
[[ -e "$FT_ROOT/training" ]] || ln -s "$REPO/training" "$FT_ROOT/training"
cd "$FT_ROOT"
mkdir -p logs
# One GPU, and data workers matched to the cores (see speedtest.sh); override by setting them before the call.
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export WORKERS="${WORKERS:-$(( $(nproc) < 14 ? $(nproc) : 14 ))}"

if want setup; then
    log "setup: Python environment and pretrained weights"
    if [[ ! -x .venv/bin/python ]] || ! cmp -s training/requirements.txt installed-requirements.txt; then
        bash training/kit/setup.sh
    else
        echo "Environment is up to date."
    fi
fi
source training/kit/env.sh

if want data; then
    log "data: Open Images -> data/full (about 200,000 images, 60 GB; resumes where it stopped)"
    if [[ -f data/full/dataset.json ]]; then
        echo "data/full is already built."
    else
        "$FT_VENV/bin/python" training/openimages.py --classes training/classes/full.txt --out data/full \
            --cache data/openimages-metadata --workers 64 --train-cap "${TRAIN_CAP:-300}"
    fi
fi

if want baseline; then
    log "baseline: the app's YOLOv8s Open Images model on the full test split (the bar to beat; 0.3454 earlier)"
    if [[ -f runs/baseline-yolov8s-oiv7-full/eval-test.json ]]; then
        echo "Baseline already scored."
    else
        "$FT_VENV/bin/python" training/evaluate.py --dataset data/full --split test --backend ultralytics \
            --weights weights/yolov8s-oiv7.pt --out runs/baseline-yolov8s-oiv7-full/eval-test.json --batch 32
    fi
fi

if want plan; then
    log "plan: measure this GPU on the real data, then choose epochs (and batch size) that fit the budget"
    : "${PRICE_PER_HOUR:?Set PRICE_PER_HOUR to the price of this machine per hour in dollars, e.g. PRICE_PER_HOUR=0.69}"
    BUDGET="${BUDGET_USD:-25}"
    rm -f overrides.env
    chosen=
    for shape in "16 1" "8 2"; do   # Batch size x accumulation; the second is for GPUs with less memory.
        set -- $shape
        if [[ -f runs/gpu-smoke-full/throughput.json ]]; then chosen="$1 $2"; break; fi
        echo "Speed test with batch size $1 x accumulation $2 ..."
        if DATASET=full SMOKE_RUN=gpu-smoke-full BATCH="$1" bash training/kit/smoke_job.sh > "logs/speed-$1x$2.log" 2>&1; then
            chosen="$1 $2"
        else
            tail -n 8 "logs/speed-$1x$2.log"
            grep -q -i "out of memory" "logs/speed-$1x$2.log" || { echo "The speed test failed (not a memory problem): logs/speed-$1x$2.log" >&2; exit 1; }
            echo "That ran out of GPU memory; trying a smaller batch."
        fi
    done
    [[ -n "$chosen" && -f runs/gpu-smoke-full/throughput.json ]] || { echo "The speed test failed; see logs/speed-*.log" >&2; exit 1; }
    set -- $chosen
    "$FT_VENV/bin/python" - "$BUDGET" "$PRICE_PER_HOUR" "$1" "$2" <<'PY'
import json, math, sys
budget, price, batch, accum = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3], sys.argv[4]
speed = json.load(open('runs/gpu-smoke-full/throughput.json'))
epoch_h = speed['estimated_minutes_per_full_epoch'] / 60 * 1.1          # +10%: validation after each epoch
hours = budget / price
spare = 2.0 + 0.35                                                       # data, baseline, scoring, export; speed test
epochs = max(1, min(40, math.floor((hours - spare) / epoch_h)))
need = epochs * epoch_h
print(f"Measured {speed['train_images_per_second']} images/s on {speed['gpu']}: one epoch is about {epoch_h * 60:.0f} min with validation.")
print(f"With ${budget:.0f} at ${price:.2f}/hour ({hours:.1f} h), after {spare:.1f} h for everything else: {epochs} epochs ({need:.1f} h, about ${need * price:.0f} of training).")
if epochs < 6:
    print("WARNING: fewer than 6 epochs fits this budget. Raise BUDGET_USD, pick a cheaper machine, or use a smaller TRAIN_CAP (rebuild data/full).")
open('overrides.env', 'w').write(f"EPOCHS={epochs}\nEPOCHS_FIXED=1\nBATCH={batch}\nACCUM={accum}\nHOURS_CAP={math.ceil(need * 1.15)}\n")
PY
fi

if want train; then
    log "train: RF-DETR Small on data/full (training/kit/full-small.env, overrides.env from the plan stage)"
    # Hard stop: a run that overruns is cut by the time cap instead of billing on (checkpoints stay; rerun resumes).
    cap=$(grep -s '^HOURS_CAP=' overrides.env | cut -d= -f2 || true)
    if [[ -n "$cap" ]]; then
        echo "Training time cap: ${cap} h"
        timeout "${cap}h" env DATASET=full MODEL=small RUN=full-small PARTS_NAME=full-train bash training/kit/train_job.sh \
            || { echo "Stopped by the time cap or an error. Rerun this stage to resume."; exit 1; }
    else
        DATASET=full MODEL=small RUN=full-small PARTS_NAME=full-train bash training/kit/train_job.sh
    fi
fi

if want report; then
    log "report: parent-aware score and class-by-class comparison with the baseline"
    bash training/kit/report_job.sh full-small
fi

if want package; then
    log "package: results to carry home (small files, then the model); copy $FT_ROOT/results off this machine"
    rm -rf results && mkdir -p results
    for file in eval-test.json compare-baseline.md rfdetr_openimages.json rfdetr_openimages.onnx metrics.csv \
                warmstart.json runs.jsonl training_config.json checkpoint_best_total.pth; do
        [[ -f "runs/full-small/$file" ]] && cp "runs/full-small/$file" results/ || echo "(no $file yet)"
    done
    cp -f runs/baseline-yolov8s-oiv7-full/eval-test.json results/baseline-eval-test.json 2>/dev/null || true
    cp -f runs/full-small/metrics-part*.csv results/ 2>/dev/null || true   # earlier sessions' history (Kaggle)
    ls -la results
fi
log "done"
