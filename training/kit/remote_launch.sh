#!/bin/bash -l
# Runs on the KIT login node, started by launch-from-windows.ps1 over SSH.
# Usage: remote_launch.sh [launch|resubmit|probe|status|sync]
#   launch    install the uploaded code, set up once, submit the pilot (refuses if jobs are active)
#   resubmit  install, cancel this project's recorded jobs that are still queued or running, submit again
#   probe     install, then ask Slurm (read-only) when differently sized jobs would start
#   status    report this project's jobs, logs and results (read-only)
#   sync      install the uploaded code only
# Submission settings come from training/kit/submit.env (committed in the repository).
set -euo pipefail
action="${1:-launch}"
NEW="$HOME/ft-training-new"
WS="$(ws_find frametrail)" || { echo "No 'frametrail' workspace. Create one with: ws_allocate frametrail 60" >&2; exit 1; }
cd "$WS/rf" 2>/dev/null || mkdir -p "$WS/rf"
cd "$WS/rf"

if [[ "$action" == status ]]; then
    exec bash "$NEW/kit/status.sh"
fi

# Extend the workspace when fewer than 14 days remain (each extension uses one of a limited number).
remaining=$(ws_list frametrail 2>/dev/null | grep -o -i 'remaining time *: *[0-9]* days' | grep -o '[0-9]*' || true)
if [[ -n "$remaining" && "$remaining" -lt 14 ]]; then
    echo "Workspace has $remaining days left; extending by 30."
    ws_extend frametrail 30
fi

rm -rf training
cp -r "$NEW" training
echo "Installed training code into $WS/rf/training"

case "$action" in
    sync) ;;
    probe) bash training/kit/probe_queue.sh ;;
    launch|resubmit)
        if [[ "$action" == resubmit && -s logs/submitted.txt ]]; then
            ids=$(awk '{print $2}' logs/submitted.txt | paste -sd,)
            active=$(squeue -h -j "$ids" -o %i 2>/dev/null || true)
            if [[ -n "$active" ]]; then
                echo "Cancelling this project's active jobs: $(echo $active)"
                scancel $active
                sleep 5
            fi
        fi
        if [[ ! -x .venv/bin/python || "${FORCE_SETUP:-0}" == 1 ]]; then
            bash training/kit/setup.sh
        fi
        set -a
        source <(tr -d '\r' < training/kit/submit.env)
        set +a
        bash training/kit/submit_pilot.sh
        ;;
    *) echo "Unknown action: $action" >&2; exit 2 ;;
esac
