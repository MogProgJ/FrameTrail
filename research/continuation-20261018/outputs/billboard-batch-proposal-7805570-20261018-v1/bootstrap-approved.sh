#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_upload="$PWD/output/frametrail-rf-billboard-batch-0a255598-v1.tar.gz"
task_actual=$(sha256sum -- "$task_upload" | awk '{print $1}')
[[ "$task_actual" == "4d8eb2e3fddda53f0d404fa3956662660bca7c69258066623bf60fac79d2543a" ]] || { echo 'Upload checksum mismatch; no extraction or submission.'; exit 1; }
task_target="$PWD/output/training-general-v1/rf-billboard-batch-0a255598-v1"
mkdir -p "$PWD/output/training-general-v1"
if [[ -e "$task_target" ]]; then
  [[ -d "$task_target" && ! -L "$task_target" && -f "$task_target/package-files.json" ]] || { echo 'Partial/unexpected target; inspect without overwrite.'; exit 1; }
else
  mkdir "$task_target"
  tar --extract --gzip --file="$task_upload" --strip-components=1 --no-same-owner --directory="$task_target"
fi
task_seal=$(sha256sum -- "$task_target/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "4dd1582ecc6d4c20c4e841b8a6fa5976fd79ef3899c5482675a2db878dd95b58" ]] || { echo 'Package identity differs; no submission.'; exit 1; }
bash "$task_target/submit.sh"
