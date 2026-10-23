#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_archive="$PWD/output/frametrail-data-refresh-2fb87eec-v1.tar.gz"
task_hash=$(sha256sum "$task_archive" | awk '{print $1}')
[[ "$task_hash" == "baf50018efc399b6e0c18df0c6ce0bd4a4d113578b015dd47226c465c6ae63a3" ]] || { echo 'Upload checksum differs; stop.'; exit 1; }
task_tools="$PWD/output/training-general-v1/data-refresh-2fb87eec-v1"
if [[ -e "$task_tools" ]]; then
  [[ -d "$task_tools" && ! -L "$task_tools" && -f "$task_tools/package-files.json" ]] || exit 1
else
  mkdir -p "$task_tools"
  tar --extract --gzip --file="$task_archive" --strip-components=1 --no-same-owner --directory="$task_tools"
fi
task_seal=$(sha256sum "$task_tools/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "ef13eafdf402fe4ba9fe28939eedf495b55a0e21885130b80aa25e8dba1697cf" ]] || { echo 'Package identity differs; stop.'; exit 1; }
bash "$task_tools/submit.sh"
