#!/bin/bash -l
#SBATCH --job-name=ft-train
#SBATCH --partition=gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x-%j.log
# Fine-tune RF-DETR on data/$DATASET, score the best checkpoint on the test split, export it for the app.
# The steps live in train_job.sh, read when the job starts. Re-submitting the same RUN resumes from
# runs/$RUN/last.ckpt, so training can span several jobs; finished runs only get scored and exported.
exec bash -l training/kit/train_job.sh
