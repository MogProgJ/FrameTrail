#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_archive="$PWD/output/frametrail-data-refresh-658b0c2c-v1.tar.gz"
task_hash=$(sha256sum "$task_archive" | awk '{print $1}')
[[ "$task_hash" == "3fc415d33c8b0edf3726c02b985a985dfb3d75ccaab13501e21ca4879bbb0653" ]] || { echo 'Upload checksum differs; stop.'; exit 1; }
task_tools="$PWD/output/training-general-v1/data-refresh-658b0c2c-v1"
if [[ -e "$task_tools" ]]; then
  [[ -d "$task_tools" && ! -L "$task_tools" && -f "$task_tools/package-files.json" ]] || exit 1
else
  mkdir -p "$task_tools"
  tar --extract --gzip --file="$task_archive" --strip-components=1 --no-same-owner --directory="$task_tools"
fi
task_seal=$(sha256sum "$task_tools/package-files.json" | awk '{print $1}')
[[ "$task_seal" == "f8fecaf5abd30a5a98efbeaf9293e96cb8e7a7ce14d29ceadf4b6b9709955034" ]] || { echo 'Package identity differs; stop.'; exit 1; }
bash "$task_tools/submit.sh"
