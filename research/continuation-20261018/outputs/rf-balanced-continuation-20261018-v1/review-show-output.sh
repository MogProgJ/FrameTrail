#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
[[ -f "$task_tools/submitted-job-id.txt" ]] || { echo 'No submission recorded. If a submission lock exists, inspect Slurm history first.'; exit 0; }
task_job=$(cat "$task_tools/submitted-job-id.txt")
[[ "$task_job" =~ ^[0-9]+$ ]] || exit 1
echo "FRAMETRAIL_JOB_ID=$task_job"
sacct -j "$task_job" --format=JobID,JobName%30,State,ExitCode,Start,Elapsed
if [[ -f "frametrail-rf-balanced-$task_job.log" ]]; then tail -n 60 "frametrail-rf-balanced-$task_job.log"; else echo 'Job log not created yet.'; fi
if [[ -f "output/rf-balanced-$task_job/experiment-report.json" ]]; then cat "output/rf-balanced-$task_job/experiment-report.json"; else echo 'Final report not ready yet.'; fi
task_sidecar="output/frametrail-rf-balanced-results-$task_job.tar.gz.sha256"
if [[ -f "$task_sidecar" ]]; then
  cat "$task_sidecar"
  task_hash=$(awk '{print $1}' "$task_sidecar")
  [[ "$task_hash" =~ ^[0-9a-f]{64}$ ]] || exit 1
  echo "FRAMETRAIL_ARCHIVE_SHA256=$task_hash"
else echo 'Result archive not ready yet.'; fi
