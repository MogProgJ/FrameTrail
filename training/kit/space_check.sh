#!/bin/bash
# Usage: space_check.sh NEED_GB  (from a job, after sourcing env.sh, which exports FT_ROOT)
# Stops a data job before it could fill the storage quota, which queued training needs for checkpoints and
# which the account shares with its other project. Read-only: queries only this user's own Lustre quota.
# Keeps RESERVE_GB (default 100) free on top of NEED_GB. If the quota cannot be read, it says so and allows.
need_gb="${1:?need GB}"
reserve_gb="${RESERVE_GB:-100}"
if ! report=$(lfs quota -q -u "$USER" "${FT_ROOT:?source env.sh first}" 2>&1); then
    echo "Could not read the storage quota (lfs quota): $report"
    echo "Continuing without a space check."
    exit 0
fi
echo "Storage quota for $USER (kbytes used, soft, hard; files used, soft, hard):"
echo "$report"
# Fields after the file system path: kbytes, quota, limit, grace, files, quota, limit, grace ('*' = over quota).
read -r used_kb limit_kb used_files limit_files <<<"$(echo $report | tr -d '*' | awk '{
    for (i = 1; i <= NF; i++) if ($i ~ /^\//) {
        print $(i+1), ($(i+3) > 0 ? $(i+3) : $(i+2)), $(i+5), ($(i+7) > 0 ? $(i+7) : $(i+6)); exit
    } }')"
if [[ -z "${limit_kb:-}" || "$limit_kb" == 0 ]]; then
    echo "No storage limit reported for this user; continuing."
    exit 0
fi
free_gb=$(( (limit_kb - used_kb) / 1024 / 1024 ))
echo "Free under the quota: $free_gb GB; this job needs about $need_gb GB plus $reserve_gb GB kept free."
if (( free_gb < need_gb + reserve_gb )); then
    echo "Not enough space: stopping before any download." >&2
    exit 1
fi
if [[ -n "${limit_files:-}" && "$limit_files" != 0 ]] && (( limit_files - used_files < 1000000 )); then
    echo "Fewer than a million files left under the quota: stopping before any download." >&2
    exit 1
fi
