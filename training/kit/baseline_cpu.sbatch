#!/bin/bash -l
#SBATCH --job-name=ft-baseline-cpu
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=10:00:00
#SBATCH --output=logs/%x-%j.log
# Score the app's YOLOv8s Open Images model on data/$DATASET's test split, on CPU (baseline.sbatch does it on a
# GPU). Used for the full vocabulary (DATASET=full): the Phase 2 bar, measured while the GPU queue is busy.
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-full}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-16}"
"$FT_VENV/bin/python" training/evaluate.py --dataset "data/$DATASET" --split test --backend ultralytics \
    --weights weights/yolov8s-oiv7.pt --out "runs/baseline-yolov8s-oiv7-$DATASET/eval-test.json" --batch 16
