#!/bin/bash -l
#SBATCH --job-name=ft-train
#SBATCH --partition=gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x-%j.log
# Fine-tune RF-DETR on data/$DATASET, then score the best checkpoint on the test split.
# Re-submitting the same RUN resumes from runs/$RUN/last.ckpt, so training can be split into
# several shorter jobs (see TRAIN_PARTS in submit_pilot.sh). Finished runs only get scored.
set -euo pipefail
source training/kit/env.sh
DATASET="${DATASET:-pilot}"
MODEL="${MODEL:-small}"
RUN="${RUN:-$DATASET-$MODEL}"
nvidia-smi
"$FT_VENV/bin/python" -c 'import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'
if [[ -f "runs/$RUN/finished.json" ]]; then
    echo "runs/$RUN already finished training."
else
    "$FT_VENV/bin/python" training/train.py --dataset "data/$DATASET" --out "runs/$RUN" --model "$MODEL" \
        --epochs "${EPOCHS:-12}" --batch-size "${BATCH:-16}" \
        --grad-accum "${ACCUM:-1}" --workers 14 --device cuda ${TRAIN_ARGS:-}
fi
[[ -f "runs/$RUN/eval-test.json" ]] || "$FT_VENV/bin/python" training/evaluate.py --dataset "data/$DATASET" --split test --backend rfdetr \
    --model-size "$MODEL" --weights "runs/$RUN/checkpoint_best_total.pth" --out "runs/$RUN/eval-test.json" --batch 16
# Once training is finished, later parts of this chain have nothing to do: cancel those that are
# still pending. Only job IDs recorded in logs/submitted.txt (this project's own) are touched.
if [[ -f "runs/$RUN/finished.json" && -s logs/submitted.txt ]]; then
    parts=$(awk '$1 == "train" {print $2}' logs/submitted.txt | paste -sd,)
    pending=$(squeue -h -t PD -j "$parts" -o %i 2>/dev/null || true)
    [[ -z "$pending" ]] || scancel $pending
fi
