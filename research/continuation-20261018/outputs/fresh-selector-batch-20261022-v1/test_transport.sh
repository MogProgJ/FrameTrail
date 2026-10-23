#!/bin/bash
# Entire scheduler/SSH surface is mocked. No network or real submission.
set -euo pipefail
task_here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_fixture="$task_here/test-fixtures/transport-$(date +%s)-$$"
mkdir -p "$task_fixture"
for task_mode in normal admission-failure ambiguous; do
  task_project="$task_fixture/$task_mode/FrameTrail"
  task_tools="$task_project/output/training-general-v1/rf-fresh-selector-v1"
  mkdir -p "$task_tools" "$task_project/.venv/bin"
  cp "$task_here/rf-fresh-selector-v1/submit.sh" "$task_here/rf-fresh-selector-v1/show-output.sh" "$task_tools/"
  cat > "$task_project/.venv/bin/python" <<'MOCKPY'
#!/bin/bash
if [[ "$2" == */admission.py ]]; then
  [[ "$TEST_MODE" != admission-failure ]] || exit 42
  echo ka_stud
fi
MOCKPY
  chmod +x "$task_project/.venv/bin/python"
  export TEST_MODE="$task_mode" TEST_LOG="$task_fixture/$task_mode/submissions.txt"
  module() { :; };scontrol() { echo 'PartitionName=gpu_a100_il'; };sacctmgr() { echo 'mock-evidence'; };squeue() { echo 'queue-evidence'; };sacct() { echo 'mock-status'; }
  sbatch() {
    printf '%s\n' "$*" >> "$TEST_LOG"
    if [[ "$1" == --test-only ]]; then echo 'estimated-start'; return 0; fi
    if [[ "$TEST_MODE" == ambiguous ]]; then echo 'unexpected-nonnumeric-reply'; else echo '123456;uc3'; fi
  }
  export -f module scontrol sacctmgr squeue sacct sbatch
  task_status=0
  bash "$task_tools/submit.sh" > "$task_fixture/$task_mode/console.txt" 2>&1 || task_status=$?
  if [[ "$task_mode" == normal ]]; then
    [[ "$task_status" == 0 && "$(cat "$task_tools/submitted-job-id.txt")" == 123456 ]]
    bash "$task_tools/submit.sh" >> "$task_fixture/$task_mode/console.txt"
    [[ "$(wc -l < "$TEST_LOG")" == 2 ]]
  elif [[ "$task_mode" == admission-failure ]]; then
    [[ "$task_status" != 0 && ! -e "$TEST_LOG" && ! -e "$task_tools/submission-lock" ]]
  else
    [[ "$task_status" != 0 && -d "$task_tools/submission-lock" && ! -e "$task_tools/submitted-job-id.txt" ]]
    bash "$task_tools/submit.sh" >> "$task_fixture/$task_mode/console.txt" 2>&1 && exit 1
    [[ "$(wc -l < "$TEST_LOG")" == 2 ]]
  fi
done
for task_script in "$task_here/START_FRESH_SELECTOR_ON_CLUSTER.sh" "$task_here/rf-fresh-selector-v1/submit.sh" "$task_here/rf-fresh-selector-v1/run-array.sbatch" "$task_here/rf-fresh-selector-v1/show-output.sh"; do bash -n "$task_script"; done
printf '{"status":"passed","real_scheduler_calls":0,"real_network_calls":0,"cases":["one array submission","recorded job idempotence","missing admission blocks","ambiguous submission retains lock and blocks replacement","all four bash scripts syntax"]}\n' > "$task_here/TRANSPORT_TEST_REPORT.json"
cat "$task_here/TRANSPORT_TEST_REPORT.json"
