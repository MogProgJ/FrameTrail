#!/bin/bash
set -euo pipefail
task_base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_name=rf-billboard-716ca2cf-v1
task_fixture="$task_base/batch-entry-fixture"
mkdir -p "$task_fixture/FrameTrail/.venv/bin" "$task_fixture/FrameTrail/output/training-general-v1/$task_name" "$task_fixture/bin"
cp "$task_base/$task_name/run-balanced.sbatch" "$task_fixture/run.sbatch"
for task_script in verify_package.py train_balanced.py bundle_results.py; do
  printf '# inert fixture; never executes Python\n' > "$task_fixture/FrameTrail/output/training-general-v1/$task_name/$task_script"
done
cat > "$task_fixture/FrameTrail/.venv/bin/python" <<'STUB'
#!/bin/bash
set -euo pipefail
while [[ "$1" == -* ]]; do shift; done
[[ -f "$1" ]] || { echo "Missing batch entry point: $1" >&2; exit 74; }
basename "$1" >> "$TEST_CALLS"
STUB
cat > "$task_fixture/bin/srun" <<'STUB'
#!/bin/bash
exec "$@"
STUB
chmod +x "$task_fixture/FrameTrail/.venv/bin/python" "$task_fixture/bin/srun"
module() { :; }; export -f module
export SLURM_SUBMIT_DIR="$task_fixture/FrameTrail" SLURM_JOB_ID=123456789
export TEST_CALLS="$task_fixture/entry-calls.txt"
[[ ! -e "$TEST_CALLS" ]]
PATH="$task_fixture/bin:$PATH" bash "$task_fixture/run.sbatch"
[[ $(cat "$TEST_CALLS") == $'verify_package.py\ntrain_balanced.py\nbundle_results.py' ]]
printf 'batch entry, training and exit-bundle paths: PASS (inert local commands only)\n'
