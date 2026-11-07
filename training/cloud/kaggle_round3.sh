#!/bin/bash
# Round 3 on Kaggle: fill in Open Images' missing labels with YOLOX-S as a teacher, then train the Phase 2 model a few
# more epochs on the same images. Why and what is measured: training/README.md ("Round 3") and AGENTS.md.
#
# Run it as the only cell of a notebook, as kaggle_run.sh does:
#   %%bash
#   git clone --depth 1 --branch claude/kind-brahmagupta-4q5cdd https://github.com/MogProgJ/FrameTrail.git /kaggle/temp/FrameTrail
#   bash /kaggle/temp/FrameTrail/training/cloud/kaggle_round3.sh
# Add the PHASE 2 notebook's final version (Version 2, "keep/full-small/checkpoint_best_total.pth") as an Input before
# the first run: Add Input -> Your Work -> that notebook -> its output. For a later session also add THIS notebook's
# earlier version the same way (both Inputs together); every keep folder under /kaggle/input is searched.
#
# Stages (ROUND3_STAGES, default "data teacher train"; each skips what is already done):
#   data     the same 38,881 training images as Phase 2 (deterministic selection; TRAIN_CAP must stay 100)
#   teacher  YOLOX-S on every validation and training image (CPU, about 1.5-2 h), precision per class against the
#            human-verified labels, then the missing boxes added to the training annotations, with audit pictures
#   train    6 more epochs from the Phase 2 checkpoint (kit/round3.env), scoring on the test split, a comparison with
#            Phase 2 and the baseline, the app model and its check
# A CPU-only session (no accelerator, which does not count against the weekly GPU hours) can run just
# "ROUND3_STAGES='data teacher'" first. Its output then holds the teacher results; the GPU session adds that output as an
# Input next to Phase 2's and runs all three stages: the teacher stage finishes at once (its results are restored) and
# only re-applies the labels to the freshly built data.
# Settings (environment variables): SESSION_HOURS (default 7: the longest the train stage may run), EPOCHS_TOTAL (6),
# TEACHER_HOURS (3: the longest the teacher stage may run; it resumes in the next session), TRAIN_CAP (100).
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$PWD"
export FT_ROOT="${FT_ROOT:-/kaggle/temp/ft}"
KEEP="${KEEP:-/kaggle/working/keep}"
INPUT="${KAGGLE_INPUT:-/kaggle/input}"
PHASE2="${PHASE2:-$REPO/training/cloud/phase2.sh}"
TRAIN_JOB="${TRAIN_JOB:-$REPO/training/kit/train_job.sh}"
TEACHER_URL="${TEACHER_URL:-https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx}"
TEACHER_SHA256="${TEACHER_SHA256:-c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063}"
export TRAIN_CAP="${TRAIN_CAP:-100}"            # Phase 2's value: the same images, so the only change is the labels
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export WORKERS="${WORKERS:-4}"
STAGES="${ROUND3_STAGES:-data teacher train}"
SESSION_HOURS="${SESSION_HOURS:-7}"
TEACHER_HOURS="${TEACHER_HOURS:-3}"
EPOCHS_TOTAL="${EPOCHS_TOTAL:-6}"
SESSION_LIMIT_HOURS="${SESSION_LIMIT_HOURS:-12}"
RUN=round3
PREVIOUS=full-small
want() { [[ " $STAGES " == *" $1 "* ]]; }
log() { printf '\n=== %s  %s\n' "$(date '+%F %T')" "$*"; }

mkdir -p "$FT_ROOT/runs" "$KEEP"
[[ -e "$FT_ROOT/training" ]] || ln -s "$REPO/training" "$FT_ROOT/training"

# What is worth keeping: small files, the model, and the audit pictures. Images are cheaper to download again.
RUN_FILES=(last.ckpt checkpoint_best_total.pth warmstart.pth warmstart.json metrics.csv runs.jsonl training_config.json
           finished.json eval-test.json eval-test-predictions.jsonl compare-baseline.md compare-phase2.md
           rfdetr_openimages.onnx rfdetr_openimages.json missing_labels.json)
save() {
    mkdir -p "$KEEP/$RUN" "$KEEP/teacher"
    for file in "${RUN_FILES[@]}"; do
        [[ -f "$FT_ROOT/runs/$RUN/$file" ]] && cp -u "$FT_ROOT/runs/$RUN/$file" "$KEEP/$RUN/$file"
    done
    for file in "$FT_ROOT"/runs/$RUN/metrics-part*.csv; do [[ -f "$file" ]] && cp -u "$file" "$KEEP/$RUN/"; done
    for file in "$FT_ROOT"/data/full/teacher-*.jsonl "$FT_ROOT/data/full/pseudo_labels.json" "$FT_ROOT/runs/$RUN/teacher-measure.json"; do
        [[ -f "$file" ]] && cp -u "$file" "$KEEP/teacher/"
    done
    [[ -d "$FT_ROOT/runs/$RUN/audit" ]] && { mkdir -p "$KEEP/teacher/audit"; cp -u "$FT_ROOT"/runs/$RUN/audit/* "$KEEP/teacher/audit/"; }
    return 0
}

log "restore: every keep folder under $INPUT (the Phase 2 checkpoint, an earlier round 3 session)"
PHASE2_KEEP=; BASELINE_KEEP=
while IFS= read -r previous; do
    echo "Found $previous"
    [[ -d "$previous/$RUN" ]] && cp -a "$previous/$RUN" "$KEEP/"            # An earlier round 3 session's run and teacher results
    [[ -d "$previous/teacher" ]] && cp -a "$previous/teacher" "$KEEP/"
    [[ -f "$previous/$PREVIOUS/checkpoint_best_total.pth" ]] && PHASE2_KEEP="$previous/$PREVIOUS"
    [[ -d "$previous/baseline" ]] && BASELINE_KEEP="$previous/baseline"
done < <(find "$INPUT" -maxdepth 6 -type d -name keep 2>/dev/null | sort)
if [[ -n "$PHASE2_KEEP" ]]; then
    mkdir -p "$FT_ROOT/runs/$PREVIOUS"
    for file in checkpoint_best_total.pth eval-test.json; do
        [[ -f "$PHASE2_KEEP/$file" ]] && cp -u "$PHASE2_KEEP/$file" "$FT_ROOT/runs/$PREVIOUS/$file"
    done
    echo "Phase 2 checkpoint: $FT_ROOT/runs/$PREVIOUS/checkpoint_best_total.pth"
elif want train; then
    echo "NO PHASE 2 CHECKPOINT FOUND (keep/$PREVIOUS/checkpoint_best_total.pth). Add the Phase 2 notebook's final version" >&2
    echo "as an Input and run again. What is under $INPUT:" >&2
    find "$INPUT" -maxdepth 3 2>/dev/null | head -n 20 >&2 || true
    exit 1
fi
if [[ -n "$BASELINE_KEEP" ]]; then
    mkdir -p "$FT_ROOT/runs/baseline-yolov8s-oiv7-full"; cp -a "$BASELINE_KEEP/." "$FT_ROOT/runs/baseline-yolov8s-oiv7-full/"
fi
if [[ -d "$KEEP/$RUN" ]]; then
    mkdir -p "$FT_ROOT/runs/$RUN"; cp -a "$KEEP/$RUN/." "$FT_ROOT/runs/$RUN/"
    echo "Restored $RUN: $(ls "$FT_ROOT/runs/$RUN" | tr '\n' ' ')"
fi
if [[ -f "$FT_ROOT/runs/$RUN/metrics.csv" ]]; then   # The trainer starts metrics.csv afresh when it resumes.
    part=1; while [[ -f "$FT_ROOT/runs/$RUN/metrics-part$part.csv" ]]; do part=$((part + 1)); done
    mv "$FT_ROOT/runs/$RUN/metrics.csv" "$FT_ROOT/runs/$RUN/metrics-part$part.csv"; rm -f "$KEEP/$RUN/metrics.csv"
fi

# A background copy every 15 minutes, and at the end however the script ends.
mkdir -p "$FT_ROOT/logs"
( while true; do sleep "${SAVE_EVERY:-900}"; save; done ) > "$FT_ROOT/logs/saver.log" 2>&1 < /dev/null & SAVER=$!
trap 'pkill -P $SAVER 2>/dev/null || true; kill $SAVER 2>/dev/null || true; save; log "saved to $KEEP"' EXIT

log "setup and data (each skips what is done)"
want train || export ALLOW_NO_GPU=1          # A CPU-only session: data and teacher only
bash "$PHASE2" setup data
source "$FT_ROOT/training/kit/env.sh"
PY="${PY:-$FT_VENV/bin/python}"
DATASET="$FT_ROOT/data/full"
[[ -f "$DATASET/dataset.json" ]] || { echo "data/full was not built" >&2; exit 1; }
mkdir -p "$FT_ROOT/runs/$RUN"
cp -u "$KEEP"/teacher/teacher-*.jsonl "$DATASET/" 2>/dev/null || true       # Earlier sessions' teacher results

if want teacher; then
    log "teacher: YOLOX-S on the validation and training images (resumes; at most $TEACHER_HOURS h per session)"
    MODEL="${TEACHER_MODEL:-$FT_ROOT/weights/yolox_s.onnx}"
    if [[ ! -f "$MODEL" ]]; then
        mkdir -p "$(dirname "$MODEL")"; curl -fL --retry 3 -o "$MODEL" "$TEACHER_URL"
    fi
    echo "$TEACHER_SHA256  $MODEL" | sha256sum -c -
    for split in valid train; do
        status=0
        timeout --kill-after=60 "${TEACHER_HOURS}h" "$PY" training/pseudo_labels.py run --dataset "$DATASET" --split "$split" \
            --teacher "$MODEL" --threads "$(nproc)" || status=$?
        save
        if [[ $status == 124 || $status == 137 ]]; then
            echo "The teacher reached its time cap ($TEACHER_HOURS h); what it did is saved."
        elif [[ $status != 0 ]]; then
            echo "The teacher failed (exit $status); see the lines above." >&2; exit 1
        fi
        "$PY" training/pseudo_labels.py status --dataset "$DATASET" --split "$split" || {
            echo "NOT FINISHED: the teacher has not run on every $split image. Start another session with this version's"
            echo "output added as an Input; it carries on from where this one stopped."; exit 0; }
    done
    log "measure the teacher per class, then fill the training annotations"
    "$PY" training/pseudo_labels.py measure --dataset "$DATASET" --split train,valid --out "$FT_ROOT/runs/$RUN/teacher-measure.json"
    "$PY" training/pseudo_labels.py fill --dataset "$DATASET" --measure "$FT_ROOT/runs/$RUN/teacher-measure.json"
    "$PY" training/pseudo_labels.py audit --dataset "$DATASET" --out "$FT_ROOT/runs/$RUN/audit" --count 24
    "$PY" training/pseudo_labels.py audit --dataset "$DATASET" --out "$FT_ROOT/runs/$RUN/audit" --count 12 --seed 5 \
        --classes "Handbag,Backpack,Umbrella,Suitcase" || true
    save
fi

if want train; then
    log "train: $EPOCHS_TOTAL epochs from the Phase 2 checkpoint on data/full with the teacher's boxes"
    "$PY" training/pseudo_labels.py status --dataset "$DATASET" --split train > /dev/null || {
        echo "The teacher has not finished (run the teacher stage first): training on half-filled labels would mix the two." >&2; exit 1; }
    [[ -f "$DATASET/train/_annotations.original.json" ]] || {
        echo "The training annotations were not filled in (run the teacher stage first)." >&2; exit 1; }
    # Time left in this session, less 40 min for scoring, the report and the export after training.
    left=$(python3 -c "print(max(0.0, round($SESSION_LIMIT_HOURS - $SECONDS / 3600 - 0.67, 2)))")
    cap=$(python3 -c "print(min($SESSION_HOURS, $left))")
    echo "Training time cap: $cap h (session limit $SESSION_LIMIT_HOURS h, $(python3 -c "print(round($SECONDS / 3600, 2))") h used)"
    if python3 -c "import sys; sys.exit(0 if $cap < 2.0 else 1)"; then
        echo "Less than 2 h left in this session: start another one (everything so far is saved)."; exit 0
    fi
    cat > "$FT_ROOT/overrides.env" <<EOF
EPOCHS=$EPOCHS_TOTAL
EPOCHS_FIXED=1
EOF
    if [[ -f "$FT_ROOT/runs/$RUN/finished.json" ]]; then
        echo "Training finished earlier; scoring and packaging again."
    fi
    timeout --kill-after=120 "${cap}h" env DATASET=full MODEL=small RUN=$RUN PARTS_NAME=round3 bash "$TRAIN_JOB" \
        || { echo "Training stopped by the session time cap or an error; the checkpoint is saved. Run again to resume."; pkill -f training/train.py || true; }
    save
    if [[ -f "$FT_ROOT/runs/$RUN/finished.json" && -f "$FT_ROOT/runs/$RUN/eval-test.json" ]]; then
        log "finished: comparison with Phase 2, then the results to download"
        [[ -f "$FT_ROOT/runs/$PREVIOUS/eval-test.json" ]] && "$PY" training/compare.py "$FT_ROOT/runs/$RUN/eval-test.json" \
            "$FT_ROOT/runs/$PREVIOUS/eval-test.json" --dataset "$DATASET" --names round3 "phase2 (full-small)" \
            --out "$FT_ROOT/runs/$RUN/compare-phase2.md" || true
        rm -rf "$KEEP/results-round3"; mkdir -p "$KEEP/results-round3"
        for file in eval-test.json compare-baseline.md compare-phase2.md rfdetr_openimages.json rfdetr_openimages.onnx metrics.csv \
                    runs.jsonl training_config.json checkpoint_best_total.pth; do
            [[ -f "$FT_ROOT/runs/$RUN/$file" ]] && cp "$FT_ROOT/runs/$RUN/$file" "$KEEP/results-round3/" || echo "(no $file)"
        done
        cp -f "$FT_ROOT/runs/$PREVIOUS/eval-test.json" "$KEEP/results-round3/phase2-eval-test.json" 2>/dev/null || true
        cp -f "$DATASET/pseudo_labels.json" "$FT_ROOT/runs/$RUN/teacher-measure.json" "$KEEP/results-round3/" 2>/dev/null || true
        cp -f "$FT_ROOT"/runs/$RUN/metrics-part*.csv "$KEEP/results-round3/" 2>/dev/null || true
        [[ -d "$FT_ROOT/runs/$RUN/audit" ]] && cp -r "$FT_ROOT/runs/$RUN/audit" "$KEEP/results-round3/"
        "$PY" - "$FT_ROOT/runs/$RUN/eval-test.json" "$FT_ROOT/runs/$PREVIOUS/eval-test.json" <<'PY' || true
import json, sys
new, old = (json.load(open(p)) for p in sys.argv[1:3])
for key, label in (('map50', 'mAP@0.5'), ('map50_people_and_vehicles', 'people and vehicles')):
    print(f'{label:22s} round3 {new[key]:.4f}   phase2 {old[key]:.4f}   change {new[key] - old[key]:+.4f}')
PY
        echo "DONE: download /kaggle/working/keep/results-round3 (the app model is rfdetr_openimages.onnx)."
    else
        echo "NOT FINISHED: start another session with this version's output added as an Input."
    fi
fi
