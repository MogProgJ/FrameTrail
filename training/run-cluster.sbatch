#!/bin/bash
# Specify an account-permitted partition when submitting; no account is committed here.
# This script assumes a prepared, pinned Linux environment and a transferred dataset bundle.
#SBATCH --job-name=frametrail-train
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=frametrail-%j.log
set -euo pipefail

: "${FT_ROOT:?Set FT_ROOT to the FrameTrail checkout on the cluster}"
: "${FT_PYTHON:?Set FT_PYTHON to the pinned CUDA environment python}"
: "${FT_DATASET:?Set FT_DATASET to the immutable dataset bundle}"
: "${FT_WEIGHTS:?Set FT_WEIGHTS to the pinned publisher checkpoint}"
: "${FT_OUTPUT:?Set FT_OUTPUT to a new persistent experiment directory}"
FT_MODE="${FT_MODE:-train}"
FT_CONFIG="${FT_CONFIG:-$FT_ROOT/training/general-cluster.json}"

cd "$FT_ROOT"
test -x "$FT_PYTHON"
test -f "$FT_DATASET/dataset-lock.json"
test -f "$FT_WEIGHTS"
# Preflight fails before GPU training if data is partial, tampered or smoke-only.
"$FT_PYTHON" -B scripts/train-detector.py --dataset "$FT_DATASET" --config "$FT_CONFIG" \
  --weights "$FT_WEIGHTS" --mode "$FT_MODE"
srun "$FT_PYTHON" -B scripts/train-detector.py --dataset "$FT_DATASET" --config "$FT_CONFIG" \
  --weights "$FT_WEIGHTS" --output "$FT_OUTPUT" --mode "$FT_MODE" --run
