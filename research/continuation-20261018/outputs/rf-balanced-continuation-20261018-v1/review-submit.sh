#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
if [[ -f "$task_tools/submitted-job-id.txt" ]]; then
  echo "Submission already recorded; no second job."
  bash "$task_tools/show-output.sh"
  exit 0
fi
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
"$PWD/.venv/bin/python" -B "$task_tools/verify_package.py"
"$PWD/.venv/bin/python" -B "$task_tools/preflight.py" --project "$PWD"
for task_script in submit.sh show-output.sh run-balanced.sbatch; do bash -n "$task_tools/$task_script"; done
task_active=$(squeue -h -u "$(id -un)" -o '%j' | awk '/^frametrail-rf/ {print}')
[[ -z "$task_active" ]] || { echo 'An existing FrameTrail RF job is active; inspect it before submission.'; exit 1; }
mkdir "$task_tools/submission-lock" || { echo 'Submission lock retained. Inspect Slurm history; do not resubmit automatically.'; exit 1; }
task_submitted=$(sbatch --parsable "$task_tools/run-balanced.sbatch")
task_job=${task_submitted%%;*}
[[ "$task_job" =~ ^[0-9]+$ ]] || { echo 'Unexpected sbatch response; lock retained.'; exit 1; }
(set -o noclobber; printf '%s\n' "$task_job" > "$task_tools/submitted-job-id.txt")
echo "Submitted ONE approved balanced continuation."
bash "$task_tools/show-output.sh"
