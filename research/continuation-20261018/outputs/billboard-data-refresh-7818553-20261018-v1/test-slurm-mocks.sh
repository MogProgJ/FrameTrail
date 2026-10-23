#!/bin/bash
set -euo pipefail
task_base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_name=data-refresh-2fb87eec-v1
task_tools="$task_base/data-tools-v1"
task_test="$task_base/slurm-mock-fixtures"
mkdir "$task_test"
module() { :; }; export -f module
for task_case in preflight-fails test-only-reject normal ambiguous; do
  task_root="$task_test/$task_case"
  task_copy="$task_root/FrameTrail/output/training-general-v1/$task_name"
  mkdir -p "$task_root/bin" "$task_root/FrameTrail/.venv/bin" "$task_copy"
  cp "$task_tools/submit.sh" "$task_tools/show-output.sh" "$task_tools/run.sbatch" "$task_copy/"
  cat > "$task_root/bin/ws_find" <<'STUB'
#!/bin/bash
printf '%s\n' "$TEST_ROOT"
STUB
  for task_cmd in squeue sacct scontrol sacctmgr; do
    printf '#!/bin/bash\nexit 0\n' > "$task_root/bin/$task_cmd"
  done
  cat > "$task_root/bin/sbatch" <<'STUB'
#!/bin/bash
if [[ "$1" == --test-only ]]; then
  [[ "$TEST_CASE" != test-only-reject ]]
  exit $?
fi
printf 'called\n' >> "$TEST_ROOT/sbatch-calls.txt"
if [[ "$TEST_CASE" == ambiguous ]]; then printf 'ambiguous-response\n'; else printf '123456789\n'; fi
STUB
  cat > "$task_root/FrameTrail/.venv/bin/python" <<'STUB'
#!/bin/bash
if [[ "$TEST_CASE" == preflight-fails ]]; then exit 73; fi
exit 0
STUB
  chmod +x "$task_root/bin/"* "$task_root/FrameTrail/.venv/bin/python"
  export TEST_ROOT="$task_root" TEST_CASE="$task_case"
  if [[ "$task_case" == normal ]]; then
    PATH="$task_root/bin:$PATH" bash "$task_copy/submit.sh" > "$task_root/first.txt" 2>&1
    PATH="$task_root/bin:$PATH" bash "$task_copy/submit.sh" > "$task_root/second.txt" 2>&1
    [[ $(wc -l < "$task_root/sbatch-calls.txt") -eq 1 ]]
  else
    if PATH="$task_root/bin:$PATH" bash "$task_copy/submit.sh" > "$task_root/first.txt" 2>&1; then exit 1; fi
    if [[ "$task_case" == ambiguous ]]; then
      if PATH="$task_root/bin:$PATH" bash "$task_copy/submit.sh" > "$task_root/second.txt" 2>&1; then exit 1; fi
      [[ $(wc -l < "$task_root/sbatch-calls.txt") -eq 1 && -d "$task_copy/submission-lock" ]]
    else
      [[ ! -e "$task_root/sbatch-calls.txt" && ! -e "$task_copy/submission-lock" ]]
    fi
  fi
  printf '%s: PASS (mock Slurm only)\n' "$task_case"
done
# Execute the real batch shell with inert Python/srun to exercise paths and traps.
task_root="$task_test/batch-entry"
task_copy="$task_root/FrameTrail/output/training-general-v1/$task_name"
mkdir -p "$task_root/bin" "$task_root/FrameTrail/.venv/bin" "$task_copy"
for task_script in collector.py bundle.py; do
  printf '# inert fixture\n' > "$task_copy/$task_script"
done
cat > "$task_root/FrameTrail/.venv/bin/python" <<'STUB'
#!/bin/bash
while [[ "$1" == -* ]]; do shift; done
[[ -f "$1" ]] || exit 74
basename "$1" >> "$TEST_CALLS"
if [[ "$1" == *collector.py && "$TEST_CASE" == training-failure ]]; then exit 73; fi
exit 0
STUB
printf '#!/bin/bash\nexec "$@"\n' > "$task_root/bin/srun"
chmod +x "$task_root/bin/srun" "$task_root/FrameTrail/.venv/bin/python"
export SLURM_SUBMIT_DIR="$task_root/FrameTrail" SLURM_JOB_ID=123456790 SLURM_ARRAY_JOB_ID=123456789 SLURM_ARRAY_TASK_ID=2 SLURM_ARRAY_TASK_COUNT=4
for TEST_CASE in normal training-failure; do
  export TEST_CASE TEST_CALLS="$task_root/$TEST_CASE-calls.txt"
  if [[ "$TEST_CASE" == normal ]]; then
    PATH="$task_root/bin:$PATH" bash "$task_tools/run.sbatch"
    [[ $(cat "$TEST_CALLS") == $'collector.py\nbundle.py' ]]
  else
    if PATH="$task_root/bin:$PATH" bash "$task_tools/run.sbatch"; then exit 1; fi
    [[ $(cat "$TEST_CALLS") == $'collector.py\nbundle.py' ]]
  fi
  printf 'batch-entry-%s: PASS (inert local commands only)\n' "$TEST_CASE"
done
