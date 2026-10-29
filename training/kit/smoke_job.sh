#!/bin/bash
# The work of a GPU smoke test; smoke.sbatch only holds the Slurm request. Two epochs on a 1,500-image slice of
# data/$DATASET, then scoring, the measured speed (runs/$SMOKE_RUN/throughput.json) and an app export.
# It proves the CUDA environment and the run's settings end to end and sizes the long run.
# From the submission: DATASET, MODEL, SMOKE_RUN (default gpu-smoke), START_FROM (optional warm start run).
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-pilot}"
MODEL="${MODEL:-small}"
SMOKE_RUN="${SMOKE_RUN:-gpu-smoke}"
nvidia-smi --query-gpu=name,memory.total --format=csv
"$FT_VENV/bin/python" training/subset.py --source "data/$DATASET" --out "data/$DATASET-smoke" \
    --train 1500 --valid 300 --test 500
rm -rf "runs/$SMOKE_RUN"
"$FT_VENV/bin/python" training/train.py --dataset "data/$DATASET-smoke" --out "runs/$SMOKE_RUN" --model "$MODEL" \
    --epochs 2 --batch-size "${BATCH:-16}" --grad-accum 1 --workers 7 --device cuda --checkpoint-interval 1 \
    ${START_FROM:+--start-from "$START_FROM"}
"$FT_VENV/bin/python" training/evaluate.py --dataset "data/$DATASET-smoke" --split test --backend rfdetr \
    --model-size "$MODEL" --weights "runs/$SMOKE_RUN/checkpoint_best_total.pth" \
    --out "runs/$SMOKE_RUN/eval-test.json" --batch 16
# One epoch = time between the two epoch checkpoints, so model loading is not counted.
"$FT_VENV/bin/python" - "$DATASET" "$SMOKE_RUN" "$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)" <<'PY'
import json, sys
from pathlib import Path
dataset, run, gpu = sys.argv[1:4]
first, second = (Path(f'runs/{run}/checkpoint_{e}.ckpt').stat().st_mtime for e in (0, 1))
epoch = second - first
roles = json.loads(Path(f'data/{dataset}/dataset.json').read_text())['roles']
full = epoch * roles['train']['images'] / 1500
result = {'gpu': gpu, 'slice_train_images': 1500, 'slice_valid_images': 300,
          'seconds_per_slice_epoch': round(epoch, 1), 'train_images_per_second': round(1500 / epoch, 1),
          'estimated_minutes_per_full_epoch': round(full / 60, 1), 'full_train_images': roles['train']['images']}
Path(f'runs/{run}/throughput.json').write_text(json.dumps(result, indent=1))
print(json.dumps(result, indent=1))
PY
# The export is checked here too, but its result must not block a training job waiting on this test (afterok):
# the training job exports by itself, and status shows this check's numbers either way.
"$FT_VENV/bin/python" training/export.py --weights "runs/$SMOKE_RUN/checkpoint_best_total.pth" --model "$MODEL" \
    --images "data/$DATASET-smoke/test" --out "runs/$SMOKE_RUN/rfdetr_openimages.onnx" --name "$SMOKE_RUN test model" \
    || echo "ONNX export check failed; see above. Training is not blocked by it."
