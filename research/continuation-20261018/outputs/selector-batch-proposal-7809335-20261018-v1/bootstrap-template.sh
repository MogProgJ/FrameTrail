#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_upload="$PWD/output/@@ARCHIVE@@"
task_actual=$(sha256sum -- "$task_upload" | awk '{print $1}')
[[ "$task_actual" == "@@ARCHIVE_SHA@@" ]] || { echo 'Upload checksum mismatch; no extraction or submission.'; exit 1; }
task_target="$PWD/output/training-general-v1/rf-selector-a77d9663-v1"
mkdir -p "$PWD/output/training-general-v1"
if [[ -e "$task_target" ]]; then
  [[ -d "$task_target" && ! -L "$task_target" && -f "$task_target/package-files.json" ]] || { echo 'Partial/unexpected target; inspect without overwrite.'; exit 1; }
else
  mkdir "$task_target"
  tar --extract --gzip --file="$task_upload" --strip-components=1 --no-same-owner --directory="$task_target"
fi
task_seal=$(sha256sum -- "$task_target/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "@@SEAL_SHA@@" ]] || { echo 'Package identity differs; no submission.'; exit 1; }
bash "$task_target/submit.sh"
