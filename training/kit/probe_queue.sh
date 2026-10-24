#!/bin/bash -l
# Read-only: ask Slurm when differently sized jobs would start. Nothing is submitted
# (sbatch --test-only). Partitions that do not exist or are not allowed show Slurm's error.
source "$(dirname "$0")/env.sh"
probe() {
    local label="$1"; shift
    local reply
    reply=$(sbatch --test-only "$@" --wrap=true 2>&1 | tail -1)
    printf '%-46s %s\n' "$label" "$(echo "$reply" | grep -o 'to start at [^ ]*' || echo "$reply")"
}
echo "Estimated start times (Slurm's estimate, often pessimistic):"
probe "cpu_il 16 CPU 8h (current data job)"   -p cpu_il -c 16 --mem=32G -t 08:00:00
probe "cpu_il 4 CPU 3h"                         -p cpu_il -c 4 --mem=16G -t 03:00:00
probe "dev_cpu_il 4 CPU 30min"                  -p dev_cpu_il -c 4 --mem=16G -t 00:30:00
probe "gpu_a100_il 1 GPU 24h (current train)"   -p gpu_a100_il --gres=gpu:1 -c 16 --mem=64G -t 24:00:00
probe "gpu_a100_il 1 GPU 8h"                    -p gpu_a100_il --gres=gpu:1 -c 16 --mem=64G -t 08:00:00
probe "gpu_a100_il 1 GPU 4h"                    -p gpu_a100_il --gres=gpu:1 -c 16 --mem=64G -t 04:00:00
probe "gpu_a100_il 1 GPU 2h"                    -p gpu_a100_il --gres=gpu:1 -c 8 --mem=32G -t 02:00:00
probe "dev_gpu_a100_il 1 GPU 30min"             -p dev_gpu_a100_il --gres=gpu:1 -c 8 --mem=32G -t 00:30:00
probe "gpu_h100 1 GPU 4h"                       -p gpu_h100 --gres=gpu:1 -c 16 --mem=64G -t 04:00:00
probe "gpu_h100_il 1 GPU 4h"                    -p gpu_h100_il --gres=gpu:1 -c 16 --mem=64G -t 04:00:00
probe "gpu_mi300 1 GPU 4h"                      -p gpu_mi300 --gres=gpu:1 -c 16 --mem=64G -t 04:00:00
