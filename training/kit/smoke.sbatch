#!/bin/bash -l
#SBATCH --job-name=ft-smoke
#SBATCH --partition=dev_gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.log
# GPU smoke test on real data: two epochs on a 1,500-image slice of data/$DATASET, then scoring.
# Proves the CUDA environment end to end and measures images/second, which sizes the long run.
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-pilot}"
MODEL="${MODEL:-small}"
nvidia-smi --query-gpu=name,memory.total --format=csv
"$FT_VENV/bin/python" training/subset.py --source "data/$DATASET" --out "data/$DATASET-smoke" \
    --train 1500 --valid 300 --test 500
rm -rf runs/gpu-smoke
"$FT_VENV/bin/python" training/train.py --dataset "data/$DATASET-smoke" --out runs/gpu-smoke --model "$MODEL" \
    --epochs 2 --batch-size "${BATCH:-16}" --grad-accum 1 --workers 7 --device cuda --checkpoint-interval 1
"$FT_VENV/bin/python" training/evaluate.py --dataset "data/$DATASET-smoke" --split test --backend rfdetr \
    --model-size "$MODEL" --weights runs/gpu-smoke/checkpoint_best_total.pth --out runs/gpu-smoke/eval-test.json --batch 16
# One epoch = time between the two epoch checkpoints, so model loading is not counted.
"$FT_VENV/bin/python" - "$DATASET" "$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)" <<'PY'
import json, sys
from pathlib import Path
dataset, gpu = sys.argv[1], sys.argv[2]
first, second = (Path(f'runs/gpu-smoke/checkpoint_{e}.ckpt').stat().st_mtime for e in (0, 1))
epoch = second - first
roles = json.loads(Path(f'data/{dataset}/dataset.json').read_text())['roles']
full = epoch * roles['train']['images'] / 1500
result = {'gpu': gpu, 'slice_train_images': 1500, 'slice_valid_images': 300,
          'seconds_per_slice_epoch': round(epoch, 1), 'train_images_per_second': round(1500 / epoch, 1),
          'estimated_minutes_per_full_epoch': round(full / 60, 1), 'full_train_images': roles['train']['images']}
Path('runs/gpu-smoke/throughput.json').write_text(json.dumps(result, indent=1))
print(json.dumps(result, indent=1))
PY
