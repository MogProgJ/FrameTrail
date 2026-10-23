#!/bin/bash
set -euo pipefail
task_base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_tools="$task_base/rf-billboard-716ca2cf-v1"
task_test="$task_base/submission-fixtures"
mkdir "$task_test"
module() { :; }; export -f module
for task_case in preflight-fails normal ambiguous; do
  task_root="$task_test/$task_case"
  mkdir -p "$task_root/bin" "$task_root/FrameTrail/.venv/bin" "$task_root/FrameTrail/output/training-general-v1/tools"
  cp "$task_tools/submit.sh" "$task_tools/show-output.sh" "$task_tools/run-balanced.sbatch" "$task_root/FrameTrail/output/training-general-v1/tools/"
  cat > "$task_root/bin/ws_find" <<'STUB'
#!/bin/bash
printf '%s\n' "$TEST_ROOT"
STUB
  cat > "$task_root/bin/squeue" <<'STUB'
#!/bin/bash
exit 0
STUB
  cat > "$task_root/bin/sacct" <<'STUB'
#!/bin/bash
printf 'MOCK status only\n'
STUB
  cat > "$task_root/bin/sbatch" <<'STUB'
#!/bin/bash
printf 'called\n' >> "$TEST_ROOT/sbatch-calls.txt"
if [[ "$TEST_CASE" == ambiguous ]]; then printf 'ambiguous-response\n'; else printf '123456789\n'; fi
STUB
  cat > "$task_root/FrameTrail/.venv/bin/python" <<'STUB'
#!/bin/bash
if [[ "$TEST_CASE" == preflight-fails ]]; then printf 'MOCK preflight rejection\n' >&2; exit 73; fi
exit 0
STUB
  chmod +x "$task_root/bin/"* "$task_root/FrameTrail/.venv/bin/python"
  export TEST_ROOT="$task_root" TEST_CASE="$task_case"
  task_path="$task_root/bin:$PATH"
  task_submit="$task_root/FrameTrail/output/training-general-v1/tools/submit.sh"
  if [[ "$task_case" == preflight-fails ]]; then
    if PATH="$task_path" bash "$task_submit" > "$task_root/first.txt" 2>&1; then exit 1; fi
    [[ ! -e "$task_root/sbatch-calls.txt" && ! -e "$(dirname "$task_submit")/submission-lock" ]]
  elif [[ "$task_case" == normal ]]; then
    PATH="$task_path" bash "$task_submit" > "$task_root/first.txt" 2>&1
    PATH="$task_path" bash "$task_submit" > "$task_root/second.txt" 2>&1
    [[ $(wc -l < "$task_root/sbatch-calls.txt") -eq 1 ]]
    [[ $(cat "$(dirname "$task_submit")/submitted-job-id.txt") == 123456789 ]]
  else
    if PATH="$task_path" bash "$task_submit" > "$task_root/first.txt" 2>&1; then exit 1; fi
    if PATH="$task_path" bash "$task_submit" > "$task_root/second.txt" 2>&1; then exit 1; fi
    [[ $(wc -l < "$task_root/sbatch-calls.txt") -eq 1 ]]
    [[ -d "$(dirname "$task_submit")/submission-lock" ]]
  fi
  printf '%s: PASS (mock Slurm only)\n' "$task_case"
done
