#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
if [[ -f "$task_tools/submitted-job-id.txt" ]]; then bash "$task_tools/show-output.sh"; exit 0; fi
module load devel/miniforge/25.3.1-python-3.12
export PYTHONDONTWRITEBYTECODE=1
"$PWD/.venv/bin/python" -B "$task_tools/collector.py" --root "$PWD" --job 0 --check-only
for task_script in submit.sh show-output.sh run.sbatch; do bash -n "$task_tools/$task_script"; done
# Authenticated evidence, not public partition maxima. Empty/failed association evidence blocks submission.
scontrol show config > "$task_tools/scheduler-config.txt" 2>&1
scontrol show partition cpu_il > "$task_tools/partition-live.txt" 2>&1
sacctmgr -nP show assoc where user="$(id -un)" format=User,Account,Partition,QOS,MaxJobs,MaxSubmitJobs,GrpTRES > "$task_tools/account-limits.txt" 2>&1
awk -F'|' -v user="$(id -un)" '$1==user && $2!="" { found=1 } END { exit !found }' "$task_tools/account-limits.txt" || { echo 'No authenticated account association; preserve evidence and stop.'; exit 1; }
squeue -u "$(id -un)" --format='%.18i %.24j %.9P %.8T %.10M %.6D %R' > "$task_tools/user-queue-before-submit.txt"
sacctmgr -nP show qos format=Name,MaxJobsPU,MaxSubmitJobsPU,MaxTRESPU,MaxWall > "$task_tools/qos-live.txt" 2>&1 || true
sbatch --test-only "$task_tools/run.sbatch" > "$task_tools/scheduler-test-only.txt" 2>&1 || { cat "$task_tools/scheduler-test-only.txt"; exit 1; }
mkdir "$task_tools/submission-lock" || { echo 'Lock retained: inspect Slurm history, never resubmit automatically.'; exit 1; }
task_reply=$(sbatch --parsable "$task_tools/run.sbatch")
task_job=${task_reply%%;*}
[[ "$task_job" =~ ^[0-9]+$ ]] || { echo 'Ambiguous sbatch response; lock retained.'; exit 1; }
(set -o noclobber; printf '%s\n' "$task_job" > "$task_tools/submitted-job-id.txt")
echo 'Submitted one bounded CPU data collection job; zero GPUs and no training.'
bash "$task_tools/show-output.sh"
