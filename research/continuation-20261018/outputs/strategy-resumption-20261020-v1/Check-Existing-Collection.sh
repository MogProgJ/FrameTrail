#!/bin/bash
# Read-only recovery check. No upload, extraction, submission, retry or replacement.
set -euo pipefail
task_workspace=$(ws_find frametrail)
[[ -n "$task_workspace" && -d "$task_workspace/FrameTrail" ]] || { echo 'FrameTrail workspace was not found.'; exit 1; }
task_tools="$task_workspace/FrameTrail/output/training-general-v1/data-refresh-2fb87eec-v1"
if [[ -f "$task_tools/submitted-job-id.txt" && -f "$task_tools/show-output.sh" ]]; then
    bash "$task_tools/show-output.sh"
else
    echo 'No recorded collection job ID. Showing recent scheduler history; no job will be submitted.'
    if [[ -d "$task_tools/submission-lock" ]]; then echo 'Existing submission lock preserved.'; fi
    sacct -u "$(id -un)" -S 2026-10-18 --format=JobID,JobName%32,State,ExitCode,Start,Elapsed
fi
