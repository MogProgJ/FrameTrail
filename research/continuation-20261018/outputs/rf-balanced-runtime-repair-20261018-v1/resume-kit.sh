#!/bin/bash
set -euo pipefail
printf '%s\n' 'FRAMETRAIL_TRANSPORT_OK=0123456789_sha256sum_$1'
cd "$(ws_find frametrail)/FrameTrail"
task_target="$PWD/output/training-general-v1/rf-balanced-ddbb57c6-v1"
[[ -d "$task_target" && ! -L "$task_target" && -f "$task_target/package-files.json" ]] || { echo 'Expected previously extracted package is missing; stop and inspect. No upload, extraction or submission attempted.'; exit 1; }
task_seal=$(sha256sum -- "$task_target/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "bff18e0df6e025551d817bd4e9ebe13f1e50b658e50fcd71b52c0873184677d0" ]] || { echo 'Package seal identity differs; stop without submission.'; exit 1; }
if [[ -f "$task_target/submitted-job-id.txt" ]]; then bash "$task_target/show-output.sh"; exit 0; fi
if [[ -d "$task_target/submission-lock" ]]; then echo 'Submission lock exists without a recorded job ID. Inspect Slurm history; no retry or new job.'; exit 1; fi
module load devel/miniforge/25.3.1-python-3.12
export PYTHONPATH="$PWD/output/rf-comparison-v1/python-overlay"
[[ -d "$PYTHONPATH" ]] || { echo 'The existing pinned RF-DETR overlay directory is missing; stop and inspect. No installation or submission.'; exit 1; }
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
printf '%s\n' "FRAMETRAIL_PREFLIGHT_OVERLAY=$PYTHONPATH"
bash "$task_target/submit.sh"
