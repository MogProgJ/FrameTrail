#!/bin/bash
set -euo pipefail
task_project="$(ws_find frametrail)/FrameTrail"
task_archive="$task_project/output/frametrail-rf-fresh-selector-v1.tar.gz"
task_actual=$(sha256sum "$task_archive" | awk '{print $1}')
[[ "$task_actual" == "b569ad8e017ac711ce9f03910de921fc8973210c29575bc28ee4d21eefc23c62" ]] || { echo 'Archive checksum differs; stop.'; exit 1; }
task_tools="$task_project/output/training-general-v1/rf-fresh-selector-v1"
if [[ -e "$task_tools" ]]; then
  [[ -d "$task_tools" && ! -L "$task_tools" && -f "$task_tools/package-files.json" ]] || exit 1
else
  mkdir "$task_tools"
  tar --extract --gzip --file="$task_archive" --strip-components=1 --no-same-owner --directory="$task_tools"
fi
task_seal=$(sha256sum "$task_tools/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "b3b48c9ccb5cfe867cbd03e2dbba86ac35b9e26b269f535c343b44168699fcf4" ]] || { echo 'Package seal differs; stop.'; exit 1; }
bash "$task_tools/submit.sh"
