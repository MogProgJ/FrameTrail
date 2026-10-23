#!/bin/bash
set -euo pipefail
printf '%s\n' 'FRAMETRAIL_TRANSPORT_OK=0123456789_sha256sum_$1'
#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_upload="$PWD/output/frametrail-rf-balanced-ddbb57c6-v1.tar.gz"
task_actual=$(sha256sum -- "$task_upload" | awk '{print $1}')
[[ "$task_actual" == "4b06118273e089b6ee283ec3aeb9abcbcc886b3622b7bc3df6df38745660960d" ]] || { echo 'Upload checksum mismatch; no extraction or submission.'; exit 1; }
task_target="$PWD/output/training-general-v1/rf-balanced-ddbb57c6-v1"
mkdir -p "$PWD/output/training-general-v1"
if [[ -e "$task_target" ]]; then
  [[ -d "$task_target" && ! -L "$task_target" && -f "$task_target/package-files.json" ]] || { echo 'Partial or unexpected target exists; inspect it. No overwrite.'; exit 1; }
else
  mkdir "$task_target"
  tar --extract --gzip --file="$task_upload" --strip-components=1 --no-same-owner --directory="$task_target"
fi
task_seal=$(sha256sum -- "$task_target/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "bff18e0df6e025551d817bd4e9ebe13f1e50b658e50fcd71b52c0873184677d0" ]] || { echo 'Package identity differs; no submission.'; exit 1; }
module load devel/miniforge/25.3.1-python-3.12
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
bash "$task_target/submit.sh"
