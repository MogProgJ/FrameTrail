#!/bin/bash -l
#SBATCH --job-name=ft-smoke
#SBATCH --partition=dev_gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.log
# GPU smoke test on real data: two short epochs, scoring, speed measurement and an app export.
# The steps live in smoke_job.sh, read when the job starts.
exec bash -l training/kit/smoke_job.sh
