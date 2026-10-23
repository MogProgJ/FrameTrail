#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
[[ -f "$task_tools/submitted-job-id.txt" ]] || { echo 'No recorded array; inspect a retained submission lock before any retry.'; exit 0; }
task_job=$(cat "$task_tools/submitted-job-id.txt")
[[ "$task_job" =~ ^[0-9]+$ ]] || exit 1
echo "FRAMETRAIL_JOB_ID=$task_job"
sacct -j "$task_job" --format=JobID,JobName%32,State,ExitCode,Start,Elapsed
for task_index in 0 1 2 3; do
  task_run="${task_job}_${task_index}"
  task_report="output/rf-billboard-batch-$task_run/experiment-report.json"
  if [[ -f "$task_report" ]]; then cat "$task_report"; else echo "Task $task_index report not ready"; fi
  task_sidecar="output/frametrail-rf-billboard-batch-results-$task_run.tar.gz.sha256"
  if [[ -f "$task_sidecar" ]]; then
    task_hash=$(awk '{print $1}' "$task_sidecar")
    [[ "$task_hash" =~ ^[0-9a-f]{64}$ ]] || exit 1
    echo "FRAMETRAIL_TASK_ARCHIVE=$task_index:$task_hash"
  else echo "Task $task_index archive not ready"; fi
done
