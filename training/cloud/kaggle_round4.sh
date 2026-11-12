#!/bin/bash
# Round 4 on Kaggle: train the round 3 model on Open Images plus COCO train2017 (fully labelled for 80 everyday types)
# with the partial-label loss. Why, and the success criteria fixed before the run: training/README.md ("Round 4") and
# AGENTS.md ("Road to a usable model").
#
# Run it as the only cell of a notebook with a GPU (T4):
#   %%bash
#   git clone --depth 1 --branch claude/kind-brahmagupta-4q5cdd https://github.com/MogProgJ/FrameTrail.git /kaggle/temp/FrameTrail
#   bash /kaggle/temp/FrameTrail/training/cloud/kaggle_round4.sh
# Add the ROUND 3 notebook's final version ("keep/round3/checkpoint_best_total.pth") as an Input before the first run:
# Add Input -> Your Work -> that notebook -> its output. For every later session also add THIS notebook's latest
# version the same way (both Inputs together); every keep folder under /kaggle/input is searched.
#
# Stages (ROUND4_STAGES, default "data check stock train"; each skips what is already done):
#   data   the same 38,881 Open Images training photos as rounds 2 and 3, stored at 640 px, plus COCO train2017
#          (about 117,000 photos, downloaded one by one: about 18 GB) with what each photo vouches for (mix_coco.py)
#   check  the pipeline's own tests in this environment, including the loss against rfdetr: a broken loss must not
#          cost GPU hours
#   stock  the stock COCO-pretrained RF-DETR Small on COCO val2017 (yardstick A), once: what this architecture
#          reaches on the 80 types. It does not stop the run if it fails
#   train  6 epochs from the round 3 checkpoint (kit/round4.env). Training stops at the end of an epoch when the
#          next one would not fit in the session, so no partial epoch is lost; the next session resumes. When the
#          last epoch is done: scoring on the Open Images test split, comparison with round 3, the app model
# Yardstick A for the trained model is scored on the laptop from the downloaded app model, with the same script and
# files as YOLOX-S and round 3.
# Settings (environment variables): EPOCHS_TOTAL (6), SESSION_LIMIT_HOURS (12, Kaggle's limit), RESERVE_HOURS (1.0,
# kept free after training for scoring and the export), COCO_CAP (unset: every usable COCO photo; a number caps the
# photos per class), COCO_IMAGES_DIR (a folder with COCO train2017 photos, e.g. an attached dataset, instead of
# downloading), TRAIN_CAP (100).
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$PWD"
export FT_ROOT="${FT_ROOT:-/kaggle/temp/ft}"
KEEP="${KEEP:-/kaggle/working/keep}"
INPUT="${KAGGLE_INPUT:-/kaggle/input}"
PHASE2="${PHASE2:-$REPO/training/cloud/phase2.sh}"
TRAIN_JOB="${TRAIN_JOB:-$REPO/training/kit/train_job.sh}"
COCO_ANNOTATIONS_URL="${COCO_ANNOTATIONS_URL:-http://images.cocodataset.org/annotations/annotations_trainval2017.zip}"
COCO_ANNOTATIONS_SHA256="${COCO_ANNOTATIONS_SHA256:-113a836d90195ee1f884e704da6304dfaaecff1f023f49b6ca93c4aaae470268}"
COCO_VAL_URL="${COCO_VAL_URL:-http://images.cocodataset.org/zips/val2017.zip}"
COCO_VAL_SHA256="${COCO_VAL_SHA256:-4f7e2ccb2866ec5041993c9cf2a952bbed69647b115d0f74da7ce8f4bef82f05}"
export TRAIN_CAP="${TRAIN_CAP:-100}"            # Rounds 2 and 3's value: the same Open Images photos
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export WORKERS="${WORKERS:-4}"
STAGES="${ROUND4_STAGES:-data check stock train}"
EPOCHS_TOTAL="${EPOCHS_TOTAL:-6}"
SESSION_LIMIT_HOURS="${SESSION_LIMIT_HOURS:-12}"
RESERVE_HOURS="${RESERVE_HOURS:-1.0}"
MIN_TRAIN_HOURS="${MIN_TRAIN_HOURS:-1.5}"
WATCH_EVERY="${WATCH_EVERY:-60}"                # Seconds between looks at the checkpoint
GRACE="${GRACE:-420}"                           # Seconds left to an epoch's validation before training is stopped
RUN=round4
PREVIOUS=round3
want() { [[ " $STAGES " == *" $1 "* ]]; }
log() { printf '\n=== %s  %s\n' "$(date '+%F %T')" "$*"; }
hours() { python3 -c "print(round($1, 2))"; }

mkdir -p "$FT_ROOT/runs" "$KEEP"
[[ -e "$FT_ROOT/training" ]] || ln -s "$REPO/training" "$FT_ROOT/training"

# What is worth keeping: small files and the model. Images are cheaper to download again.
RUN_FILES=(last.ckpt checkpoint_best_total.pth warmstart.pth warmstart.json metrics.csv runs.jsonl training_config.json
           finished.json eval-test.json eval-test-predictions.jsonl compare-baseline.md compare-round3.md
           rfdetr_openimages.onnx rfdetr_openimages.json missing_labels.json mix_coco.json
           yardstick-stock-rfdetr-small.jsonl yardstick-stock.md yardstick-stock.json)
save() {
    mkdir -p "$KEEP/$RUN"
    for file in "${RUN_FILES[@]}"; do
        [[ -f "$FT_ROOT/runs/$RUN/$file" ]] && cp -u "$FT_ROOT/runs/$RUN/$file" "$KEEP/$RUN/$file"
    done
    for file in "$FT_ROOT"/runs/$RUN/metrics-part*.csv; do [[ -f "$file" ]] && cp -u "$file" "$KEEP/$RUN/"; done
    return 0
}

log "restore: every keep folder under $INPUT (the round 3 checkpoint, an earlier round 4 session)"
PREVIOUS_KEEP=; BASELINE_KEEP=
while IFS= read -r previous; do
    echo "Found $previous"
    [[ -d "$previous/$RUN" ]] && cp -a "$previous/$RUN" "$KEEP/"            # An earlier round 4 session
    [[ -f "$previous/$PREVIOUS/checkpoint_best_total.pth" ]] && PREVIOUS_KEEP="$previous/$PREVIOUS"
    [[ -d "$previous/baseline" ]] && BASELINE_KEEP="$previous/baseline"
done < <(find "$INPUT" -maxdepth 6 -type d -name keep 2>/dev/null | sort)
if [[ -n "$PREVIOUS_KEEP" ]]; then
    mkdir -p "$FT_ROOT/runs/$PREVIOUS"
    for file in checkpoint_best_total.pth eval-test.json; do
        [[ -f "$PREVIOUS_KEEP/$file" ]] && cp -u "$PREVIOUS_KEEP/$file" "$FT_ROOT/runs/$PREVIOUS/$file"
    done
    echo "Round 3 checkpoint: $FT_ROOT/runs/$PREVIOUS/checkpoint_best_total.pth"
elif want train && [[ ! -f "$KEEP/$RUN/last.ckpt" ]]; then
    echo "NO ROUND 3 CHECKPOINT FOUND (keep/$PREVIOUS/checkpoint_best_total.pth). Add the round 3 notebook's final version" >&2
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
WATCHER=
trap '[[ -n "$WATCHER" ]] && kill $WATCHER 2>/dev/null; pkill -P $SAVER 2>/dev/null || true; kill $SAVER 2>/dev/null || true; save; log "saved to $KEEP"' EXIT

log "setup and Open Images data (each skips what is done)"
want train || want stock || export ALLOW_NO_GPU=1
bash "$PHASE2" setup data
source "$FT_ROOT/training/kit/env.sh"
PY="${PY:-$FT_VENV/bin/python}"
DATASET="$FT_ROOT/data/full"
COCO="$FT_ROOT/data/coco"
[[ -f "$DATASET/dataset.json" ]] || { echo "data/full was not built" >&2; exit 1; }
mkdir -p "$FT_ROOT/runs/$RUN" "$COCO/annotations"

fetch() {   # fetch URL FILE SHA256: download (resuming) and check
    for attempt in 1 2 3 4 5; do curl -fL --retry 3 -C - -o "$2" "$1" && break; sleep 10; done
    echo "$3  $2" | sha256sum -c -
}
unpack() {  # unpack ZIP FOLDER [MEMBER ...]: Python, so it needs no unzip program
    "$PY" - "$@" <<'PY'
import sys, zipfile
archive, folder, members = sys.argv[1], sys.argv[2], sys.argv[3:]
with zipfile.ZipFile(archive) as z:
    z.extractall(folder, members or None)
PY
}

if want data; then
    if "$PY" training/mix_coco.py status --dataset "$DATASET" > /dev/null; then
        echo "COCO is already in data/full."
    else
        log "data: Open Images training photos to 640 px (COCO's size), then COCO train2017 and what each photo vouches for"
        "$PY" training/mix_coco.py shrink --dataset "$DATASET" --split train --max-side 640 --workers "$(nproc)"
        if [[ ! -f "$COCO/annotations/instances_train2017.json" || ! -f "$COCO/annotations/instances_val2017.json" ]]; then
            fetch "$COCO_ANNOTATIONS_URL" "$COCO/annotations.zip" "$COCO_ANNOTATIONS_SHA256"
            unpack "$COCO/annotations.zip" "$COCO" annotations/instances_train2017.json annotations/instances_val2017.json
            rm -f "$COCO/annotations.zip"
        fi
        "$PY" training/mix_coco.py add --dataset "$DATASET" --annotations "$COCO/annotations/instances_train2017.json" \
            --workers 64 ${COCO_CAP:+--cap "$COCO_CAP"} ${COCO_IMAGES_DIR:+--images-dir "$COCO_IMAGES_DIR"}
    fi
    cp -f "$DATASET/mix_coco.json" "$FT_ROOT/runs/$RUN/mix_coco.json"
    df -h "$FT_ROOT" | tail -n 1
    save
fi

if want check; then
    log "check: the pipeline's tests in this environment (the loss against rfdetr included)"
    ( cd "$REPO" && "$PY" -m unittest tests.test_mix_coco tests.test_training_pipeline 2>&1 | tail -n 12 ) || {
        echo "The tests failed here; training would run on code that does not do what it should. Nothing was trained." >&2; exit 1; }
fi

if want stock && [[ ! -f "$FT_ROOT/runs/$RUN/yardstick-stock.json" ]]; then
    log "stock: the COCO-pretrained RF-DETR Small on COCO val2017 (yardstick A); a failure here does not stop the run"
    stock() {
        if [[ ! -d "$COCO/val2017" ]]; then
            fetch "$COCO_VAL_URL" "$COCO/val2017.zip" "$COCO_VAL_SHA256" || return 1
            unpack "$COCO/val2017.zip" "$COCO" || return 1
            rm -f "$COCO/val2017.zip"
        fi
        timeout 30m "$PY" training/coco_yardstick.py predict-rfdetr --images "$COCO/val2017"             --out "$FT_ROOT/runs/$RUN/yardstick-stock-rfdetr-small.jsonl" || return 1
        "$PY" training/coco_yardstick.py score --annotations "$COCO/annotations/instances_val2017.json"             --model "stock-rfdetr-small=$FT_ROOT/runs/$RUN/yardstick-stock-rfdetr-small.jsonl"             --out "$FT_ROOT/runs/$RUN/yardstick-stock.md" | head -n 16
    }
    stock || echo "The stock model was not scored (see above); carrying on."
    save
fi

watch_epochs() {   # Stop training at the end of an epoch when another one would not fit before $1 (in $SECONDS).
    local deadline=$1 checkpoint="$FT_ROOT/runs/$RUN/last.ckpt" seen now started=$SECONDS epoch left
    seen=$(stat -c %Y "$checkpoint" 2>/dev/null || echo 0)
    while sleep "$WATCH_EVERY"; do
        [[ -f "$FT_ROOT/runs/$RUN/finished.json" ]] && return 0
        now=$(stat -c %Y "$checkpoint" 2>/dev/null || echo 0)
        [[ "$now" == "$seen" ]] && continue
        seen=$now; epoch=$((SECONDS - started)); started=$SECONDS; left=$((deadline - SECONDS))
        echo "An epoch finished after $(hours "$epoch / 3600") h; $(hours "$left / 3600") h of training time left in this session."
        if (( left < epoch * 11 / 10 + GRACE )); then
            echo "Another epoch would not fit: stopping here, at an epoch boundary. The next session resumes."
            sleep "$GRACE"
            [[ -f "$FT_ROOT/runs/$RUN/finished.json" ]] || pkill -f training/train.py || true
            return 0
        fi
    done
}

if want train; then
    log "train: $EPOCHS_TOTAL epochs from the round 3 checkpoint on Open Images plus COCO"
    "$PY" training/mix_coco.py status --dataset "$DATASET" > /dev/null || {
        echo "COCO is not in data/full (run the data stage first): this would be round 3's data again." >&2; exit 1; }
    [[ -f "$FT_ROOT/runs/$RUN/last.ckpt" || -f "$FT_ROOT/runs/$PREVIOUS/checkpoint_best_total.pth" ]] || {
        echo "Neither a round 4 checkpoint to resume nor the round 3 checkpoint to start from." >&2; exit 1; }
    cap=$(python3 -c "print(max(0.0, round($SESSION_LIMIT_HOURS - $SECONDS / 3600 - $RESERVE_HOURS, 2)))")
    echo "Training time in this session: $cap h (limit $SESSION_LIMIT_HOURS h, $(hours "$SECONDS / 3600") h used, $RESERVE_HOURS h kept for scoring)"
    if python3 -c "import sys; sys.exit(0 if $cap < $MIN_TRAIN_HOURS else 1)"; then
        echo "Too little time left in this session: start another one (everything so far is saved)."; exit 0
    fi
    cat > "$FT_ROOT/overrides.env" <<EOF
EPOCHS=$EPOCHS_TOTAL
EPOCHS_FIXED=1
EOF
    [[ -f "$FT_ROOT/runs/$RUN/finished.json" ]] && echo "Training finished earlier; scoring and packaging again."
    deadline=$(python3 -c "print(int($SECONDS + $cap * 3600))")
    watch_epochs "$deadline" & WATCHER=$!
    # The hard stop covers scoring and the export after the last epoch too, so it sits later than the epoch watcher's.
    hard=$(python3 -c "print(round($cap + $RESERVE_HOURS * 0.9, 3))")
    timeout --kill-after=120 "${hard}h" env DATASET=full MODEL=small RUN=$RUN PARTS_NAME=round4 bash "$TRAIN_JOB" \
        || { echo "Training stopped (epoch boundary, time cap or an error; see above). The checkpoint is saved."; pkill -f training/train.py || true; }
    kill "$WATCHER" 2>/dev/null || true; WATCHER=
    save
    if [[ -f "$FT_ROOT/runs/$RUN/finished.json" && -f "$FT_ROOT/runs/$RUN/eval-test.json" ]]; then
        log "finished: comparison with round 3, then the results to download"
        [[ -f "$FT_ROOT/runs/$PREVIOUS/eval-test.json" ]] && "$PY" training/compare.py "$FT_ROOT/runs/$RUN/eval-test.json" \
            "$FT_ROOT/runs/$PREVIOUS/eval-test.json" --dataset "$DATASET" --names round4 round3 \
            --out "$FT_ROOT/runs/$RUN/compare-round3.md" || true
        rm -rf "$KEEP/results-round4"; mkdir -p "$KEEP/results-round4"
        for file in eval-test.json compare-baseline.md compare-round3.md rfdetr_openimages.json rfdetr_openimages.onnx metrics.csv \
                    runs.jsonl training_config.json missing_labels.json mix_coco.json warmstart.json \
                    yardstick-stock-rfdetr-small.jsonl yardstick-stock.md yardstick-stock.json checkpoint_best_total.pth; do
            [[ -f "$FT_ROOT/runs/$RUN/$file" ]] && cp "$FT_ROOT/runs/$RUN/$file" "$KEEP/results-round4/" || echo "(no $file)"
        done
        cp -f "$FT_ROOT/runs/$PREVIOUS/eval-test.json" "$KEEP/results-round4/round3-eval-test.json" 2>/dev/null || true
        cp -f "$FT_ROOT"/runs/$RUN/metrics-part*.csv "$KEEP/results-round4/" 2>/dev/null || true
        [[ -f "$FT_ROOT/runs/$PREVIOUS/eval-test.json" ]] && "$PY" - "$FT_ROOT/runs/$RUN/eval-test.json" "$FT_ROOT/runs/$PREVIOUS/eval-test.json" <<'PY' || true
import json, sys
new, old = (json.load(open(p)) for p in sys.argv[1:3])
for key, label in (('map50', 'mAP@0.5'), ('map50_people_and_vehicles', 'people and vehicles')):
    print(f'{label:22s} round4 {new[key]:.4f}   round3 {old[key]:.4f}   change {new[key] - old[key]:+.4f}')
PY
        # One file to download, at the top of the Output tab: everything but the checkpoint (that stays in keep/ for later runs).
        "$PY" - "$KEEP/results-round4" "$(dirname "$KEEP")/results-round4.zip" <<'PY' || true
import pathlib, sys, zipfile
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(src.rglob('*')):
        if f.is_file() and f.suffix != '.pth':
            z.write(f, pathlib.Path('results-round4') / f.relative_to(src))
print(f'{out}: {out.stat().st_size / 1e6:.0f} MB')
PY
        echo "DONE: download results-round4.zip from the top of the Output tab (the app model is rfdetr_openimages.onnx inside)."
    else
        echo "NOT FINISHED: start another session with this version's output added as an Input (next to round 3's)."
    fi
fi
