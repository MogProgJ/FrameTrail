#!/bin/bash -l
#SBATCH --job-name=ft-export
#SBATCH --partition=dev_cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.log
# Export a run's best checkpoint as the app's rfdetr-oi ONNX file, on CPU. Training jobs export by themselves;
# this is for runs that did not, such as the GPU smoke test (RUN=gpu-smoke, the default). Its 2-epoch model is
# only good for checking that the app loads the profile and runs it on the laptop's GPU, not for accuracy.
set -euo pipefail
source training/kit/env.sh
RUN="${RUN:-gpu-smoke}"
MODEL="${MODEL:-small}"
IMAGES="${IMAGES:-data/pilot-smoke/test}"
NAME="${NAME:-$RUN test model}"
"$FT_VENV/bin/python" training/export.py --weights "runs/$RUN/checkpoint_best_total.pth" --model "$MODEL" \
    --images "$IMAGES" --out "runs/$RUN/rfdetr_openimages.onnx" --name "$NAME"
