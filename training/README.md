# RF-DETR training pipeline

Fine-tunes RF-DETR on Open Images V7 and scores it against the YOLOv8s Open Images model the app already ships. The goal and rules are in [AGENTS.md](../AGENTS.md).

| File | Job |
| --- | --- |
| `classes/pilot.txt` | The 110 pilot classes. `Target = Source, Source` merges Open Images classes (e.g. Man/Woman/Boy/Girl into Person). |
| `openimages.py` | Downloads Open Images metadata and images; writes `train/`, `valid/` and `test/` in rfdetr's COCO layout, plus `dataset.json`. |
| `train.py` | Fine-tunes the whole model and resumes automatically if re-run. |
| `warmstart.py` | Gives each class that also exists in COCO its pretrained COCO head row. Without it, rfdetr's resizing gives our first class COCO's unused slot, and the smoke test then never detected Person at all. |
| `evaluate.py` + `oi_metric.py` | Open Images-style mAP@0.5. Classes are only scored on images where they were human-verified, group-of boxes count once, and merged classes are de-duplicated. |
| `kit/` | bwUniCluster setup and Slurm jobs. |

Splits: training uses Open Images *train*, checkpoint selection uses *validation*, and the reported score uses *test*. The pilot takes up to 600 training images per class, choosing the rarest classes first. A dry run against the real metadata selected 49,418 training images (~179k boxes, roughly 14 GB), 1,954 validation and 4,774 test images. Rare Open Images classes stay thin: Towel has 144 training images, and Scissors has only 6 test images, so its score is noisy.

To preview the selection without downloading images, add `--plan-only` to the `openimages.py` command. It needs about 3 GB of metadata and about a minute.

## Run the pilot on the KIT cluster

The cluster is only reachable from your laptop, because the SSH key lives there. Cloud sessions cannot connect.

**One command, from the laptop** (PowerShell in the FrameTrail folder, with the Interactive key unlocked):

```powershell
git fetch origin
git checkout claude/kind-brahmagupta-4q5cdd
powershell -ExecutionPolicy Bypass -File training\kit\launch-from-windows.ps1
```

This copies `training/` to the cluster and runs `kit/remote_launch.sh` on the login node, which:

1. Extends the `frametrail` workspace by 30 days if fewer than 14 remain.
2. Puts the code in `$(ws_find frametrail)/rf/training`.
3. Prints the partition time limits.
4. Runs `kit/setup.sh` the first time (several GB of packages plus the pretrained weights). Set `FORCE_SETUP=1` to redo it.
5. Runs `kit/submit_pilot.sh`. That script has Slurm validate all three requests (`sbatch --test-only`) before queuing anything, and refuses to submit while an earlier FrameTrail chain is still active.

The job scripts assume `cpu_il` allows 8 hours and `gpu_a100_il` allows 24 hours. If the printed limits are shorter, lower `--time` in the matching `training/kit/*.sbatch`. Training resumes when re-submitted.

To do the same by hand in a cluster terminal: copy `training/` into `$(ws_find frametrail)/rf/`, `cd` there, then run `bash training/kit/setup.sh` and `bash training/kit/submit_pilot.sh`.

The pilot chain:

| Job | Resources | What it does |
| --- | --- | --- |
| `ft-prepare` | `cpu_il`, 16 CPUs, 32 GB, up to 8 h | Builds `data/pilot` (~6 GB metadata + ~16 GB images) |
| `ft-train` | `gpu_a100_il`, 1 A100, 16 CPUs, 64 GB, up to 24 h | RF-DETR Small, 12 epochs, then scores the test split |
| `ft-baseline` | `gpu_a100_il`, 1 A100, up to 2 h | Scores YOLOv8s Open Images on the same test split |

Timings are estimates until the first run measures them.

**6. Follow progress.** This queries only the FrameTrail job IDs recorded at submission, never the whole shared account:

```bash
squeue -j "$(awk '{print $2}' logs/submitted.txt | paste -sd,)"
tail -f logs/ft-train-*.log
cat runs/pilot-small/metrics.csv | tail -3
```

**7. Results.** Two files hold the answer:

- `runs/pilot-small/eval-test.json`: our model's scores.
- `runs/baseline-yolov8s-oiv7-pilot/eval-test.json`: the baseline's scores.

Each holds `map50`, `map50_people_and_vehicles` and per-class AP. Copy them back to the laptop (small files) or paste the summary lines from the logs.

If training stops at the time limit, resubmit only the training job and it resumes:

```bash
sbatch training/kit/train.sbatch
```

## Local smoke test (any machine, CPU)

Builds a tiny 4-class dataset from the Open Images *validation* split, trains for one epoch and scores it. It takes about five minutes and is only a pipeline check, not a quality measure.

```bash
python -m venv .venv && .venv/bin/pip install -r training/requirements.txt
.venv/bin/python training/openimages.py --classes training/classes/smoke.txt --out data/smoke --smoke \
    --train-cap 20 --valid-cap 4 --test-cap 6 --workers 16
.venv/bin/python training/train.py --dataset data/smoke --out runs/smoke --epochs 1 --batch-size 2 \
    --grad-accum 1 --workers 2 --device cpu
.venv/bin/python training/evaluate.py --dataset data/smoke --backend rfdetr \
    --weights runs/smoke/checkpoint_best_total.pth --out runs/smoke/eval-test.json --batch 4
```

Unit tests for the pure logic, which need no packages: `python -m unittest tests.test_training_pipeline`.

## Known limits

- Open Images labels are incomplete. Training treats unlabeled objects as background, the same as public Open Images detectors do. Evaluation corrects for this; training does not yet (Phase 3 in AGENTS.md).
- Group-of boxes, which cover a crowd of the same objects, are trained as ordinary boxes.
- Merging Man/Woman/Boy/Girl into Person removes near-duplicate boxes at IoU 0.7. An image verified to contain no Man is treated as verified for Person.
