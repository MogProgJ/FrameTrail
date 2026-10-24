#!/bin/bash -l
#SBATCH --job-name=ft-baseline
#SBATCH --partition=gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x-%j.log
# Score the app's current broad model (YOLOv8s Open Images V7) on the same test split.
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-pilot}"
"$FT_VENV/bin/python" training/evaluate.py --dataset "data/$DATASET" --split test --backend ultralytics \
    --weights weights/yolov8s-oiv7.pt --out "runs/baseline-yolov8s-oiv7-$DATASET/eval-test.json" --batch 32
