#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
[[ -f "$task_tools/submitted-job-id.txt" ]] || { echo 'No recorded data job; inspect retained submission lock before any action.'; exit 0; }
task_job=$(cat "$task_tools/submitted-job-id.txt")
[[ "$task_job" =~ ^[0-9]+$ ]] || exit 1
echo "FRAMETRAIL_JOB_ID=$task_job"
sacct -j "$task_job" --format=JobID,JobName%32,State,ExitCode,Start,Elapsed
task_report="output/billboard-data-refresh-$task_job/collection-report.json"
if [[ -f "$task_report" ]]; then cat "$task_report"; printf '\n'; else echo 'Collection report not ready.'; fi
task_sidecar="output/frametrail-data-refresh-results-$task_job.tar.gz.sha256"
if [[ -f "$task_sidecar" ]]; then task_hash=$(awk '{print $1}' "$task_sidecar"); [[ "$task_hash" =~ ^[0-9a-f]{64}$ ]] || exit 1; echo "FRAMETRAIL_ARCHIVE_SHA256=$task_hash"; else echo 'Archive not ready.'; fi
