# RF-DETR training pipeline

Fine-tunes RF-DETR on Open Images V7 and scores it against the YOLOv8s Open Images model the app already ships. The goal and rules are in [AGENTS.md](../AGENTS.md).

| File | Job |
| --- | --- |
| `classes/pilot.txt` | The 110 pilot classes. `Target = Source, Source` merges Open Images classes (e.g. Man/Woman/Boy/Girl into Person). |
| `openimages.py` | Downloads Open Images metadata and images; writes `train/`, `valid/` and `test/` in rfdetr's COCO layout, plus `dataset.json`. |
| `train.py` | Fine-tunes the whole model and resumes automatically if re-run. |
| `warmstart.py` | Gives each class that also exists in COCO its pretrained COCO head row. Without it, rfdetr's resizing gives our first class COCO's unused slot, and the smoke test then never detected Person at all. |
| `evaluate.py` + `oi_metric.py` | Open Images-style mAP@0.5. Classes are only scored on images where they were human-verified, group-of boxes count once, and merged classes are de-duplicated. |
| `export.py` | Writes the app's ONNX file for the `rfdetr-oi` profile: boxes plus one logit per app category (615), with each trained class placed in its app category through the app's own Open Images name table. It checks the ONNX output against PyTorch and writes a `.json` summary next to it. |
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

This copies `training/` to the cluster and runs `kit/remote_launch.sh` on the login node. That script extends the workspace when fewer than 14 days remain, installs the code into `$(ws_find frametrail)/rf/training`, runs `kit/setup.sh` the first time (`FORCE_SETUP=1` redoes it), and submits. `submit_pilot.sh` has Slurm validate every request (`sbatch --test-only`) before queuing anything, and refuses while an earlier FrameTrail chain is still active.

Other actions, all with the same script and `-Action <name>`:

| Action | What it does |
| --- | --- |
| `status` | Read-only report: queue state and estimated start of this project's jobs, recent log lines, epoch metrics, test scores |
| `probe` | Read-only: asks Slurm when differently sized jobs would start (`sbatch --test-only`, nothing queued) |
| `resubmit` | Cancels this project's recorded jobs that are still queued or running, then submits again with `kit/submit.env` |
| `sync` | Only installs the uploaded code (and updates `.venv` when `requirements.txt` changed) |

`kit/submit.env` holds the submission settings in Git. It is set from the queue probe:

1. The data job runs as up to three resumable 30-minute parts in `dev_cpu_il`.
2. Then a 30-minute GPU smoke test runs in `dev_gpu_a100_il` (`kit/smoke.sbatch`). It trains two epochs on a 1,500-image slice, scores it, and writes `runs/gpu-smoke/throughput.json` with images per second and the estimated minutes per full epoch.
3. The baseline scoring also runs in `dev_gpu_a100_il`.
4. Finally, one 24-hour training job may start on `gpu_h100_il`, `gpu_h100` or `gpu_a100_il`, whichever is first. It only starts if the smoke test passed.

`kit/train.env` (epochs, batch size) is read when the training job starts. Change it, then `-Action sync`, and a queued job picks it up without losing its place. `TRAIN_PARTS` can split training into back-to-back jobs that resume, and a finished run cancels its own leftover parts. That only helps when waits depend on job length; on 2026-10-24 they depended on priority. The data job is skipped once `data/<dataset>/dataset.json` exists. `sinfo` is not permitted for this account, so `probe` is how to compare queues.

`resubmit` first has Slurm validate the new requests and only then cancels the old ones. If a dev queue refuses some optional jobs (later data parts, the baseline, the smoke test), the rest is still submitted, and every queued job is recorded in `logs/submitted.txt`.

To work by hand in a cluster terminal instead: copy `training/` into `$(ws_find frametrail)/rf/`, `cd` there, then run `bash training/kit/setup.sh` and `bash training/kit/submit_pilot.sh`.

The pilot chain:

| Job | Resources (from `kit/submit.env`) | What it does |
| --- | --- | --- |
| `ft-prepare` | `dev_cpu_il`, 4 CPUs, 16 GB, 30-minute parts that resume | Builds `data/pilot` (~6 GB metadata + ~16 GB images) |
| `ft-smoke` | `dev_gpu_a100_il`, 1 A100, 30 min | Two short epochs, scoring, speed measurement |
| `ft-baseline` | `dev_gpu_a100_il`, 1 A100, 30 min | Scores YOLOv8s Open Images on the test split |
| `ft-train` | `gpu_h100_il`, `gpu_h100` or `gpu_a100_il`, 1 GPU, 16 CPUs, 64 GB, up to 24 h | RF-DETR Small, 50 epochs (cosine schedule), then scores the test split and exports the app model |

Measured on 2026-10-24: the data job took 15 minutes in `cpu_il`; the smoke test trained at 62.5 images/s on an A100 (about 13 minutes per pilot epoch). The 50-epoch length is an estimate of 11–13 h on an A100.

**Follow progress** with `-Action status`. It only queries the FrameTrail job IDs recorded at submission, never the whole shared account.

**Results.** Two files hold the answer:

- `runs/pilot-small/eval-test.json`: our model's scores.
- `runs/baseline-yolov8s-oiv7-pilot/eval-test.json`: the baseline's scores.

Each holds `map50`, `map50_people_and_vehicles` and per-class AP. The training job also writes `runs/pilot-small/rfdetr_openimages.onnx`, the app-ready model, with its `.json` parity summary. Copy them back to the laptop (small files) or paste the summary lines from the logs.

If training stops at the time limit, resubmit only the training job and it resumes:

```bash
sbatch training/kit/train.sbatch
```

## Use a trained model in the app

Copy `runs/<run>/rfdetr_openimages.onnx` (about 115 MB for RF-DETR Small) into the app's `models/` folder, restart FrameTrail, and pick **RF-DETR · Open Images (trained)**. From the command line: `--model-type rfdetr-oi`.

The app accepts the file because of its metadata (profile `rfdetr-oi`, the 615-category vocabulary and the 512 px preprocessing), not a pinned checksum, so every retrained model drops in the same way. Classes the model was not trained on are never reported. Saved runs, tracking, appearance counting and CSV export work as with the other models, because classes keep the app's usual category IDs.

Checked on 2026-10-24 with a small test checkpoint: the app's own detector code (built on Linux against ONNX Runtime 1.30) loaded the export and returned the same detections as rfdetr. Files with a wrong profile or preprocessing were refused, and saved runs, new and old, opened correctly. The Windows build and the DirectML GPU path were not tested in that session.

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
