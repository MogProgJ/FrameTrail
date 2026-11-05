#!/bin/bash
# The work of a training job; train.sbatch only holds the Slurm request. This file is read when the job starts,
# so fixes synced while a job waits in the queue still apply (Slurm keeps the batch script as submitted).
# From the submission: DATASET, MODEL, RUN, and PARTS_NAME (the name its parts are recorded under).
# From training/kit/<RUN>.env if it exists, else training/kit/train.env: EPOCHS, BATCH, ACCUM, START_FROM.
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-pilot}"
MODEL="${MODEL:-small}"
RUN="${RUN:-$DATASET-$MODEL}"
PARTS_NAME="${PARTS_NAME:-train}"
settings="training/kit/$RUN.env"
[[ -f "$settings" ]] || settings=training/kit/train.env
echo "Run $RUN on data/$DATASET; settings from $settings:"
grep -v '^#' "$settings"
source <(tr -d '\r' < "$settings")
# Settings chosen for this machine (training/cloud/phase2.sh plan stage: epochs, batch size from a measured speed).
[[ -f "$FT_ROOT/overrides.env" ]] && { echo "Overrides:"; cat "$FT_ROOT/overrides.env"; source "$FT_ROOT/overrides.env"; }
# Without the run to start from (e.g. after the cluster was lost), train from the official COCO weights.
if [[ -n "${START_FROM:-}" && ! -f "$START_FROM" ]]; then
    echo "START_FROM $START_FROM is missing; starting from the COCO weights instead."
    START_FROM=
fi
nvidia-smi
"$FT_VENV/bin/python" -c 'import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'
# Epochs may depend on the GPU the job landed on (EPOCHS_H100, EPOCHS_A100), so one 24 h job fits either way.
# A resumed run keeps the count it started with (train.py).
gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
if [[ -z "${EPOCHS_FIXED:-}" ]]; then
    case "$gpu" in
        *H100*) EPOCHS="${EPOCHS_H100:-${EPOCHS:-12}}" ;;
        *A100*) EPOCHS="${EPOCHS_A100:-${EPOCHS:-12}}" ;;
    esac
fi
echo "GPU: $gpu; epochs: ${EPOCHS:-12}"
if [[ -f "runs/$RUN/finished.json" ]]; then
    echo "runs/$RUN already finished training."
else
    "$FT_VENV/bin/python" training/train.py --dataset "data/$DATASET" --out "runs/$RUN" --model "$MODEL" \
        --epochs "${EPOCHS:-12}" --batch-size "${BATCH:-16}" --grad-accum "${ACCUM:-1}" --workers "${WORKERS:-14}" --device cuda \
        ${START_FROM:+--start-from "$START_FROM"} ${TRAIN_ARGS:-}
fi
[[ -f "runs/$RUN/eval-test.json" ]] || "$FT_VENV/bin/python" training/evaluate.py --dataset "data/$DATASET" \
    --split test --backend rfdetr --model-size "$MODEL" --weights "runs/$RUN/checkpoint_best_total.pth" \
    --out "runs/$RUN/eval-test.json" --batch 16
# Parent-aware score and a class-by-class comparison with the baseline, when the baseline has been scored.
bash training/kit/report_job.sh "$RUN" || echo "Report failed; see above."
# App-ready ONNX for the "RF-DETR · Open Images (trained)" profile. A failed export does not fail the job;
# -Action add -Job ...-model can redo it, and -Action fetch only installs a file whose check passed.
ONNX="runs/$RUN/rfdetr_openimages.onnx"
grep -q '"passed": true' "runs/$RUN/rfdetr_openimages.json" 2>/dev/null || "$FT_VENV/bin/python" training/export.py \
    --weights "runs/$RUN/checkpoint_best_total.pth" --model "$MODEL" --images "data/$DATASET/test" --out "$ONNX" \
    --name "RF-DETR ${MODEL^} · Open Images ($RUN)" || echo "ONNX export failed; see above."
# Once training is finished, later parts of this run have nothing to do: cancel those still pending. Only job IDs
# this project recorded under PARTS_NAME (logs/submitted.txt, logs/extra.txt) are touched.
if [[ -f "runs/$RUN/finished.json" ]]; then
    parts=$(cat logs/submitted.txt logs/extra.txt 2>/dev/null | awk -v name="$PARTS_NAME" '$1 == name {print $2}' | paste -sd, || true)
    pending=$( [[ -z "$parts" ]] || squeue -h -t PD -j "$parts" -o %i 2>/dev/null || true)
    [[ -z "$pending" ]] || scancel $pending
fi
