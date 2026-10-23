#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_upload="$PWD/output/frametrail-rf-selector-a77d9663-v1.tar.gz"
task_actual=$(sha256sum -- "$task_upload" | awk '{print $1}')
[[ "$task_actual" == "18e774efc73f126ffb5e5de2f648e2a5385c06ff4dffd422e309a27d0bc3235c" ]] || { echo 'Upload checksum mismatch; no extraction or submission.'; exit 1; }
task_target="$PWD/output/training-general-v1/rf-selector-a77d9663-v1"
mkdir -p "$PWD/output/training-general-v1"
if [[ -e "$task_target" ]]; then
  [[ -d "$task_target" && ! -L "$task_target" && -f "$task_target/package-files.json" ]] || { echo 'Partial/unexpected target; inspect without overwrite.'; exit 1; }
else
  mkdir "$task_target"
  tar --extract --gzip --file="$task_upload" --strip-components=1 --no-same-owner --directory="$task_target"
fi
task_seal=$(sha256sum -- "$task_target/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "9d8009c09ed03b4e01397fb9b4d346baeb1560f3c2007ba46a8cab8c9923d885" ]] || { echo 'Package identity differs; no submission.'; exit 1; }
bash "$task_target/submit.sh"
