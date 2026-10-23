#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_project=$(cd -- "$task_tools/../../.." && pwd)
task_job=$(cat "$task_tools/submitted-job-id.txt")
[[ "$task_job" =~ ^[1-9][0-9]*$ ]] || exit 1
echo "FRAMETRAIL_JOB_ID=$task_job"
sacct -j "$task_job" --format=JobID,JobName%32,State,ExitCode,Start,Elapsed
for task_index in 0 1; do
  task_out="$task_project/output/rf-fresh-selector-${task_job}_${task_index}"
  if [[ -f "$task_out/REPORT.json" ]]; then cat "$task_out/REPORT.json"; elif [[ -f "$task_out/FAILED.json" ]]; then cat "$task_out/FAILED.json"; else echo "Task $task_index report not ready"; fi
  task_archive="$task_project/output/frametrail-fresh-selector-results-${task_job}_${task_index}.tar.gz"
  if [[ -f "$task_archive.sha256" ]]; then cat "$task_archive.sha256"; else echo "Task $task_index archive not ready"; fi
done
