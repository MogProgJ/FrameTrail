#!/bin/bash -l
#SBATCH --job-name=ft-report
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%j.log
# Re-score saved predictions with the parent-aware score and compare runs with the baseline; see report_job.sh.
exec bash -l training/kit/report_job.sh
