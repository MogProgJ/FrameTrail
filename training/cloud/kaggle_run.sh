#!/bin/bash
# One Kaggle session of the Phase 2 run. Run it as the only cell of a notebook and use "Save Version" -> "Save & Run All":
# that runs in the background for up to 12 hours with the GPU, without the browser open, and keeps /kaggle/working as
# the version's output. A second session continues from that output (add it as an Input, see below), until the run
# is finished. Sized from the speed test on a T4 (12.7 images/s at batch size 8, two GPUs visible, one used):
#   100 images per class = 38,881 training images, 0.94 h per epoch with validation, 20 epochs = 18.7 h = two sessions.
#
#   %%bash
#   git clone --depth 1 --branch claude/kind-brahmagupta-4q5cdd https://github.com/MogProgJ/FrameTrail.git /kaggle/temp/FrameTrail
#   bash /kaggle/temp/FrameTrail/training/cloud/kaggle_run.sh
# (Clone into /kaggle/temp, not /kaggle/working: the working folder is saved as output, and the default branch alone has
# 28,000 files.)
#
# Session 1: sets up, downloads the data (about 13 GB), scores the YOLOv8 baseline, trains until SESSION_HOURS are used.
# Session 2: add session 1's output as an Input (Add Input -> Your Work / Notebook Output -> this notebook -> latest
#   version), run again: it restores the checkpoint from /kaggle/input/*/keep and carries on. Repeat until the log says
#   "training finished". Results end up in /kaggle/working/keep/results of the last version: download them.
# Settings (environment variables): SESSION_HOURS (default 10: training time per session; setup, data and baseline take
#   about 1 h more, and a session ends at 12 h), EPOCHS_TOTAL (default 20), TRAIN_CAP (default 100).
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$PWD"
export FT_ROOT="${FT_ROOT:-/kaggle/temp/ft}"
KEEP="${KEEP:-/kaggle/working/keep}"
INPUT="${KAGGLE_INPUT:-/kaggle/input}"
PHASE2="${PHASE2:-$REPO/training/cloud/phase2.sh}"
export TRAIN_CAP="${TRAIN_CAP:-100}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export WORKERS="${WORKERS:-4}"
SESSION_HOURS="${SESSION_HOURS:-10}"
EPOCHS_TOTAL="${EPOCHS_TOTAL:-20}"
RUN=runs/full-small
log() { printf '\n=== %s  %s\n' "$(date '+%F %T')" "$*"; }

mkdir -p "$FT_ROOT/runs" "$KEEP"
[[ -e "$FT_ROOT/training" ]] || ln -s "$REPO/training" "$FT_ROOT/training"

# Small, valuable files only: Kaggle keeps at most 20 GB of output, and the images are cheaper to download again.
FILES=(last.ckpt checkpoint_best_total.pth warmstart.pth warmstart.json metrics.csv runs.jsonl training_config.json
       finished.json eval-test.json eval-test-predictions.jsonl compare-baseline.md rfdetr_openimages.onnx rfdetr_openimages.json)
save() {
    mkdir -p "$KEEP/full-small" "$KEEP/baseline"
    for file in "${FILES[@]}"; do
        [[ -f "$FT_ROOT/$RUN/$file" ]] && cp -u "$FT_ROOT/$RUN/$file" "$KEEP/full-small/$file"
    done
    [[ -f "$FT_ROOT/runs/baseline-yolov8s-oiv7-full/eval-test.json" ]] \
        && cp -u "$FT_ROOT/runs/baseline-yolov8s-oiv7-full/eval-test"* "$KEEP/baseline/" || true
}

log "restore: look for the previous session's output under $INPUT/*/keep"
for previous in "$INPUT"/*/keep; do
    [[ -d "$previous" ]] || continue
    echo "Found $previous"
    cp -a "$previous/." "$KEEP/"
done
if [[ -d "$KEEP/full-small" ]]; then
    mkdir -p "$FT_ROOT/$RUN"; cp -a "$KEEP/full-small/." "$FT_ROOT/$RUN/"
    echo "Restored the run: $(ls "$FT_ROOT/$RUN" | tr '\n' ' ')"
fi
if [[ -d "$KEEP/baseline" ]]; then
    mkdir -p "$FT_ROOT/runs/baseline-yolov8s-oiv7-full"; cp -a "$KEEP/baseline/." "$FT_ROOT/runs/baseline-yolov8s-oiv7-full/"
fi
if [[ -f "$FT_ROOT/$RUN/finished.json" && -f "$FT_ROOT/$RUN/eval-test.json" ]]; then
    log "training finished earlier; packaging the results again"
    bash "$PHASE2" package || true; save
    cp -a "$FT_ROOT/results" "$KEEP/" 2>/dev/null || true
    exit 0
fi

# A background copy every 15 minutes, and at the end however the script ends: an interrupted session keeps its last checkpoint.
# Its output goes to a file: a loop holding the cell's output pipe would keep the cell running after the script ends.
mkdir -p "$FT_ROOT/logs"
( while true; do sleep "${SAVE_EVERY:-900}"; save; done ) > "$FT_ROOT/logs/saver.log" 2>&1 < /dev/null & SAVER=$!
trap 'pkill -P $SAVER 2>/dev/null || true; kill $SAVER 2>/dev/null || true; save; log "saved to $KEEP"' EXIT

log "setup, data and baseline (each skips what is done)"
bash "$PHASE2" setup data baseline
cat > "$FT_ROOT/overrides.env" <<EOF
EPOCHS=$EPOCHS_TOTAL
EPOCHS_FIXED=1
BATCH=8
ACCUM=2
HOURS_CAP=$SESSION_HOURS
EOF
echo "Plan: $EPOCHS_TOTAL epochs in total (an estimated $(python3 -c "print(round($EPOCHS_TOTAL*0.94,1))") GPU hours), at most $SESSION_HOURS h of training in this session."

log "train (resumes from last.ckpt when the previous session left one)"
bash "$PHASE2" train || echo "Training stopped by the session time cap or an error; the checkpoint is saved."
if [[ -f "$FT_ROOT/$RUN/finished.json" ]]; then
    log "training finished: scoring, report and export ran inside the train stage; packaging"
    bash "$PHASE2" package || true
    cp -a "$FT_ROOT/results" "$KEEP/" 2>/dev/null || true
    echo "DONE: download /kaggle/working/keep/results (the app model is rfdetr_openimages.onnx)."
else
    echo "NOT FINISHED: start another session with this version's output added as an Input."
    grep -c . "$FT_ROOT/$RUN/metrics.csv" 2>/dev/null | xargs -I{} echo "Metrics rows so far: {}"
fi
