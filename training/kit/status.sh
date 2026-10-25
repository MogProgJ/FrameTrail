#!/bin/bash -l
# Read-only progress report for this project's own jobs (IDs from logs/submitted.txt and logs/extra.txt).
source "$(dirname "$0")/env.sh"
if [[ ! -s logs/submitted.txt && ! -s logs/extra.txt ]]; then echo "No FrameTrail submission recorded."; exit 0; fi
cat logs/submitted.txt 2>/dev/null
[[ -s logs/extra.txt ]] && { echo "Extra jobs:"; cat logs/extra.txt; }
echo; echo "Training settings on the cluster (read when the training job starts):"
grep -v "^#" training/kit/train.env
ids=$(cat logs/submitted.txt logs/extra.txt 2>/dev/null | awk '{print $2}' | paste -sd,)
echo; echo "Queue (empty = finished or cancelled):"
squeue -j "$ids" -o "%.10i %.12j %.9T %.20S %.10M %R" 2>/dev/null || true
echo; echo "Finished jobs:"
sacct -j "$ids" -X -o JobID,JobName%12,State,Elapsed,ExitCode 2>/dev/null || true
# A log's own last lines, without the resource summary Slurm appends to every job log.
log_tail() {
    awk '/JOB FEEDBACK|^Job ID: [0-9]+$/ {exit} {print}' "$1" \
        | grep -v -E '^(CPU Utilized|CPU Efficiency|Job Wall-clock time|Memory Utilized|Memory Efficiency|NodeName=|Cluster:|User/Group:|State:|Nodes:|Cores per node:)' \
        | tail -n "$2"
}
for log in $(ls -t logs/ft-*.log 2>/dev/null | head -3); do
    echo; echo "== last lines of $log"; log_tail "$log" 5
done
# Failed jobs show more, so the error is visible without opening the cluster.
sacct -j "$ids" -X -n -P -o JobID,JobName,State 2>/dev/null | while IFS='|' read -r id name state; do
    [[ "$state" =~ ^(FAILED|OUT_OF_MEMORY|NODE_FAIL) && -f "logs/$name-$id.log" ]] || continue
    echo; echo "== $name $id $state: last lines of logs/$name-$id.log"; log_tail "logs/$name-$id.log" 25
done
for metrics in runs/*/metrics.csv; do
    [[ -f "$metrics" ]] && { echo; echo "== $metrics (last epoch rows)"; tail -n 2 "$metrics" | cut -c1-200; }
done
if [[ -d data/full ]]; then
    echo; echo "== data/full: $(find data/full -name '*.jpg' | wc -l) images so far$([[ -f data/full/dataset.json ]] && echo ', complete')"
fi
if [[ -f runs/gpu-smoke/throughput.json ]]; then echo; echo "== GPU smoke speed"; cat runs/gpu-smoke/throughput.json; fi
for result in runs/*/eval-test.json; do
    [[ -f "$result" ]] && { echo; echo "== $result"; "$FT_VENV/bin/python" -c "
import json, sys
r = json.load(open(sys.argv[1]))
print('mAP@0.5', round(r['map50'], 4), '| people/vehicles', round(r['map50_people_and_vehicles'] or 0, 4),
      '| classes', r['classes_scored'], '| images', r['images'])" "$result"; }
done
for summary in runs/*/rfdetr_openimages.json; do
    [[ -f "$summary" ]] && { echo; echo "== $summary"; "$FT_VENV/bin/python" -c "
import json, sys
r = json.load(open(sys.argv[1]))
print('ONNX', r['onnx'], '| classes', r['classes'], '| parity passed', r['parity']['passed'])" "$summary"; }
done
true
