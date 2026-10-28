#!/bin/bash
# Re-score every finished run from its saved predictions (adding the parent-aware score; the flat score does not
# change) and compare each RF-DETR run with the YOLOv8s baseline on the same dataset (runs/<run>/compare-baseline.md).
# CPU only; no model is loaded. Run by report.sbatch, and by train_job.sh for its own run.
# Usage: report_job.sh [RUN...]  (default: every run with scores)
set -euo pipefail
source training/kit/env.sh
runs=("$@")
[[ ${#runs[@]} -gt 0 ]] || runs=($(ls -d runs/*/ 2>/dev/null | xargs -n1 basename))
for run in "${runs[@]}"; do
    scores="runs/$run/eval-test.json"
    predictions="runs/$run/eval-test-predictions.jsonl"
    [[ -f "$scores" && -f "$predictions" ]] || continue
    # Keep the dataset and the model the scores came from (paths here contain no spaces).
    recorded=$("$FT_VENV/bin/python" -c "
import json, sys; r = json.load(open(sys.argv[1]))
print('--dataset', r['dataset'], *(['--backend', r['backend']] if r.get('backend') else []),
      *(['--weights', r['weights']] if r.get('weights') else []))" "$scores")
    echo "== $run ($recorded)"
    "$FT_VENV/bin/python" training/evaluate.py $recorded --split test --predictions "$predictions" --out "$scores"
done
for run in "${runs[@]}"; do
    scores="runs/$run/eval-test.json"
    [[ -f "$scores" && "$run" != baseline-* ]] || continue
    dataset=$("$FT_VENV/bin/python" -c "import json, sys; print(json.load(open(sys.argv[1]))['dataset'])" "$scores")
    baseline="runs/baseline-yolov8s-oiv7-$(basename "$dataset")/eval-test.json"
    [[ -f "$baseline" ]] || continue
    "$FT_VENV/bin/python" training/compare.py "$scores" "$baseline" --dataset "$dataset" \
        --names "$run" "YOLOv8s (app baseline)" --out "runs/$run/compare-baseline.md"
done
