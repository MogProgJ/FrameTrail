#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_project=$(cd -- "$task_tools/../../.." && pwd)
if [[ -f "$task_tools/submitted-job-id.txt" ]]; then bash "$task_tools/show-output.sh"; exit 0; fi
[[ ! -e "$task_tools/submission-lock" ]] || { echo 'Submission previously attempted; inspect evidence. No replacement.'; exit 1; }
module load devel/miniforge/25.3.1-python-3.12
export PYTHONPATH="$task_project/output/rf-comparison-v1/python-overlay"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
task_python="$task_project/.venv/bin/python"
"$task_python" -B "$task_tools/verify_package.py" --project "$task_project"
mkdir "$task_tools/admission"
task_user=$(id -un)
scontrol show partition gpu_a100_il > "$task_tools/admission/partition-live.txt"
sacctmgr -nP show user where name="$task_user" format=User,DefaultAccount > "$task_tools/admission/user-default.txt"
sacctmgr -nP show assoc where user="$task_user" format=User,Account,Partition,QOS,MaxJobs,MaxSubmitJobs,GrpTRES > "$task_tools/admission/account-limits.txt"
sacctmgr -nP show qos format=Name,MaxJobsPU,MaxSubmitJobsPU,MaxTRESPU,MaxWall > "$task_tools/admission/qos-live.txt"
squeue -u "$task_user" --format='%.18i %.20j %.10T %.10M %.30b' > "$task_tools/admission/queue-live.txt"
task_account=$("$task_python" -B "$task_tools/admission.py" "$task_tools/admission")
cd "$task_project"
sbatch --test-only --account="$task_account" --chdir="$task_project" --output="$task_tools/slurm-%A_%a.out" "$task_tools/run-array.sbatch" "$task_tools" > "$task_tools/admission/admission-test.txt" 2>&1
mkdir "$task_tools/submission-lock"
# Keep lock even if SSH dies after sbatch: ambiguity never authorizes replacement.
task_reply=$(sbatch --parsable --account="$task_account" --chdir="$task_project" --output="$task_tools/slurm-%A_%a.out" "$task_tools/run-array.sbatch" "$task_tools")
printf '%s\n' "$task_reply" > "$task_tools/admission/submission-reply.txt"
task_job=${task_reply%%;*}
[[ "$task_job" =~ ^[1-9][0-9]*$ ]] || { echo 'Ambiguous submission; preserve lock and inspect scheduler.'; exit 1; }
(set -o noclobber; printf '%s\n' "$task_job" > "$task_tools/submitted-job-id.txt")
echo "Submitted one fixed two-task array. FRAMETRAIL_JOB_ID=$task_job"
bash "$task_tools/show-output.sh"
