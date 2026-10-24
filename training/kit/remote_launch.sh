#!/bin/bash -l
# Runs on the KIT login node (started by launch-from-windows.ps1 over SSH).
# Installs the freshly copied training folder into the workspace, sets up the
# environment the first time (or with FORCE_SETUP=1) and submits the pilot chain.
set -euo pipefail
NEW="$HOME/ft-training-new"
WS="$(ws_find frametrail)" || { echo "No 'frametrail' workspace. Create one with: ws_allocate frametrail 60" >&2; exit 1; }

# Extend the workspace when fewer than 14 days remain (each extension uses one of a limited number).
remaining=$(ws_list frametrail 2>/dev/null | grep -o -i 'remaining time *: *[0-9]* days' | grep -o '[0-9]*' || true)
if [[ -n "$remaining" && "$remaining" -lt 14 ]]; then
    echo "Workspace has $remaining days left; extending by 30."
    ws_extend frametrail 30
elif [[ -z "$remaining" ]]; then
    echo "Could not read the workspace lifetime; check 'ws_list' yourself." >&2
fi

mkdir -p "$WS/rf"
rm -rf "$WS/rf/training"
cp -r "$NEW" "$WS/rf/training"
cd "$WS/rf"
echo "Partition limits:"
sinfo -p cpu_il,gpu_a100_il -o "%P %l %G %a" || true

if [[ ! -x .venv/bin/python || "${FORCE_SETUP:-0}" == 1 ]]; then
    bash training/kit/setup.sh
fi
bash training/kit/submit_pilot.sh
