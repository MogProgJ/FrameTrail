#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_archive="$PWD/output/frametrail-data-refresh-2fb87eec-v1-r2.tar.gz"
task_hash=$(sha256sum "$task_archive" | awk '{print $1}')
[[ "$task_hash" == "3b639df7064cefa9e15f99f9b2061c9c45c00aae53a27453cf2d9b42a852ae3e" ]] || { echo 'Upload checksum differs; stop.'; exit 1; }
task_tools="$PWD/output/training-general-v1/data-refresh-2fb87eec-v1"
if [[ -e "$task_tools" ]]; then
  [[ -d "$task_tools" && ! -L "$task_tools" && -f "$task_tools/package-files.json" ]] || exit 1
else
  mkdir -p "$task_tools"
  tar --extract --gzip --file="$task_archive" --strip-components=1 --no-same-owner --directory="$task_tools"
fi
task_seal=$(sha256sum "$task_tools/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "b509f3dbabbff41397d2228b204e583fd9ce25584c0503ae48e3d027897d7302" ]] || { echo 'Package identity differs; stop.'; exit 1; }
bash "$task_tools/submit.sh"
