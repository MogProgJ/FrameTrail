#!/bin/bash
# Quick check of a GPU machine before any real money or quota is spent: about 30-40 minutes, mostly setup.
# Works on Kaggle (internet on, GPU on), Colab, RunPod, Vast.ai, Azure: any Linux with an NVIDIA GPU.
#
#   git clone https://github.com/MogProgJ/FrameTrail.git && cd FrameTrail && git checkout claude/kind-brahmagupta-4q5cdd
#   bash training/cloud/speedtest.sh
#
# It sets up Python 3.12 and the packages, downloads a small probe set of Open Images (about 2,000 images, plus 6 GB
# of metadata), trains 2 epochs on 1,500 of them, and prints how fast this GPU trains and what that means for the
# real run. It tests everything a real run needs: internet, disk, Python, memory, and mixed precision on this GPU.
# Where to work: $FT_ROOT (default ~/frametrail-work; on Kaggle use FT_ROOT=/kaggle/temp/ft).
set -euo pipefail
cd "$(dirname "$0")/../.."
REPO="$PWD"
command -v nvidia-smi >/dev/null || { echo "No NVIDIA GPU: on Kaggle turn on Settings > Accelerator > GPU, and Internet." >&2; exit 1; }
nvidia-smi --query-gpu=name,memory.total --format=csv
df -h "${FT_ROOT:-$HOME}" 2>/dev/null | tail -1 | awk '{print "Free disk here: " $4}'
export FT_ROOT="${FT_ROOT:-$HOME/frametrail-work}"
mkdir -p "$FT_ROOT"
[[ -e "$FT_ROOT/training" ]] || ln -s "$REPO/training" "$FT_ROOT/training"
cd "$FT_ROOT"; mkdir -p logs
echo "== setup (a few minutes)"
bash training/kit/setup.sh > logs/setup.log 2>&1 || { tail -n 20 logs/setup.log; echo "Setup failed; see $FT_ROOT/logs/setup.log" >&2; exit 1; }
source training/kit/env.sh
if [[ ! -f data/probe/dataset.json ]]; then
    echo "== probe data (downloads about 6 GB of metadata, then about 2,000 images)"
    "$FT_VENV/bin/python" training/openimages.py --classes training/classes/full.txt --out data/probe \
        --cache data/openimages-metadata --workers 32 --train-cap 5 --valid-cap 2 --test-cap 3
fi
echo "== speed test: 2 short epochs on this GPU"
for batch in 16 8; do
    if DATASET=probe SMOKE_RUN=gpu-probe BATCH="$batch" bash training/kit/smoke_job.sh > "logs/speed-$batch.log" 2>&1; then
        echo "Batch size $batch worked."; break
    fi
    tail -n 5 "logs/speed-$batch.log"; echo "Batch size $batch failed (out of memory?); trying a smaller one."
    [[ "$batch" != 8 ]] || { echo "The speed test failed; see $FT_ROOT/logs/speed-*.log" >&2; exit 1; }
done
"$FT_VENV/bin/python" - <<'PY'
import json
speed = json.load(open('runs/gpu-probe/throughput.json'))
rate = speed['train_images_per_second']
print(f"\nThis GPU ({speed['gpu']}) trains at {rate} images/s.")
print("For comparison: an A100 80 GB did 55.6 images/s on the same test (the cluster measurement).\n")
print("What that means for the real run (epochs x images / speed, +10% for validation):")
print(f"{'training set':<28}{'images':>9}{'hours per epoch':>18}{'20 epochs':>12}")
for label, images in (('100 per class (about 13 GB)', 38881), ('200 per class', 72660), ('300 per class (default)', 102598), ('600 per class', 175051)):
    hours = images / rate / 3600 * 1.1
    print(f"{label:<28}{images:>9}{hours:>18.1f}{hours * 20:>10.0f} h")
print("\nAt the cluster's A100 speed the default set takes 0.5 h per epoch; at a tenth of that speed, 5 h.")
print("Kaggle's free quota is about 30 GPU hours a week in sessions of at most 12 hours (check the quota page).")
PY
echo "Done. Nothing here is needed afterwards; delete the machine or session."
