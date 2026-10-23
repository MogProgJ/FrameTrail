#!/bin/bash
set -euo pipefail
task_project="$(ws_find frametrail)/FrameTrail"
task_archive="$task_project/output/frametrail-rf-fresh-selector-v1.tar.gz"
task_actual=$(sha256sum "$task_archive" | awk '{print $1}')
[[ "$task_actual" == "fc4fd7683dc6e2f71f7140573f4478d6fbf60ea5f36f82f4233aabea993642a1" ]] || { echo 'Archive checksum differs; stop.'; exit 1; }
task_tools="$task_project/output/training-general-v1/rf-fresh-selector-v1"
if [[ -e "$task_tools" ]]; then
  [[ -d "$task_tools" && ! -L "$task_tools" && -f "$task_tools/package-files.json" ]] || exit 1
else
  mkdir "$task_tools"
  tar --extract --gzip --file="$task_archive" --strip-components=1 --no-same-owner --directory="$task_tools"
fi
task_seal=$(sha256sum "$task_tools/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "4f5a277801496f554e682505353ab5c25b8f86fc6771316e71d4bb90fae3ad08" ]] || { echo 'Package seal differs; stop.'; exit 1; }
bash "$task_tools/submit.sh"
