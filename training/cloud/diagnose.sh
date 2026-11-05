#!/bin/bash
# What is left after a crash or a killed notebook kernel: the newest logs, memory, GPU memory, biggest processes.
# Usage: FT_ROOT=/kaggle/temp/ft bash training/cloud/diagnose.sh
FT_ROOT="${FT_ROOT:-$HOME/frametrail-work}"
echo "== logs in $FT_ROOT/logs"; ls -t "$FT_ROOT/logs" 2>/dev/null | head -5
for log in $(ls -t "$FT_ROOT"/logs/speed-*.log 2>/dev/null | head -1); do echo "== end of $log"; tail -n 25 "$log"; done
echo "== memory (GB)"; free -g | head -2
echo "== GPU memory"; nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv 2>&1 | head -4
echo "== biggest processes"; ps aux --sort=-rss | head -6 | cut -c1-160
echo "== kernel messages about memory (may be unavailable)"; dmesg 2>/dev/null | grep -i -E "killed process|out of memory|oom" | tail -3 || true
