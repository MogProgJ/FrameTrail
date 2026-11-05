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
#   RUN_DEATH_SWITCH=1   power the machine off when the script ends or fails (stops the per-hour billing; it does not
#                        delete the disk). Leave unset to keep it on.
#   TRAIN_ARGS           extra train.py options, e.g. "--unverified-weight 0.25"
# Settings (epochs, batch size, run to start from) are in training/kit/full-small.env, as on the cluster.
set -euo pipefail
cd "$(dirname "$0")/../.."
STAGES=("$@"); [[ ${#STAGES[@]} -gt 0 ]] || STAGES=(setup data baseline train report package)
log() { printf '\n=== %s  %s\n' "$(date '+%F %T')" "$*"; }
want() { [[ " ${STAGES[*]} " == *" $1 "* ]]; }

if [[ "${RUN_DEATH_SWITCH:-0}" == 1 ]]; then
    trap 'log "Finished or failed; powering off (RUN_DEATH_SWITCH=1)"; sync; sudo poweroff' EXIT
fi
command -v nvidia-smi >/dev/null || { echo "No NVIDIA GPU driver found (nvidia-smi missing)." >&2; exit 1; }
nvidia-smi --query-gpu=name,memory.total --format=csv

# The repository's scripts expect to run from $FT_ROOT with training/ inside it.
REPO="$PWD"
export FT_ROOT="${FT_ROOT:-$HOME/frametrail-work}"
mkdir -p "$FT_ROOT"
[[ -e "$FT_ROOT/training" ]] || ln -s "$REPO/training" "$FT_ROOT/training"
cd "$FT_ROOT"
mkdir -p logs

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
            --cache data/openimages-metadata --workers 64
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

if want train; then
    log "train: RF-DETR Small on data/full (training/kit/full-small.env)"
    DATASET=full MODEL=small RUN=full-small PARTS_NAME=full-train bash training/kit/train_job.sh
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
    ls -la results
fi
log "done"
