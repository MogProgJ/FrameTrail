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

**1. Laptop (PowerShell, in your FrameTrail checkout).** Get this branch and copy the `training` folder to your cluster home:

```powershell
git fetch origin
git checkout claude/kind-brahmagupta-4q5cdd
scp -r .\training ka_udxvl@uc3.scc.kit.edu:~/ft-training
```

**2. Cluster terminal.** Check the workspace, which was due to expire on 3 November, extend it, and put the code in place:

```bash
ws_list
ws_extend frametrail 30
mkdir -p "$(ws_find frametrail)/rf"
rm -rf "$(ws_find frametrail)/rf/training"
cp -r ~/ft-training "$(ws_find frametrail)/rf/training"
cd "$(ws_find frametrail)/rf"
```

**3. Check the partition limits** before submitting, because the job scripts assume `cpu_il` allows 8 hours and `gpu_a100_il` allows 24 hours:

```bash
sinfo -p cpu_il,gpu_a100_il -o "%P %l %G %a"
```

If a limit is shorter, lower `--time` in the matching `training/kit/*.sbatch` file. Training resumes when re-submitted, so a shorter limit only means more submissions.

**4. One-time environment setup** on the login node. It downloads several GB of Python packages and the pretrained weights:

```bash
bash training/kit/setup.sh
```

**5. Submit the pilot.** This submits three jobs. The data job runs first, then training and the baseline run in parallel:

```bash
bash training/kit/submit_pilot.sh
```

| Job | Resources | What it does |
| --- | --- | --- |
| `ft-prepare` | `cpu_il`, 16 CPUs, 64 GB, up to 8 h | Builds `data/pilot` (~6 GB metadata + ~16 GB images) |
| `ft-train` | `gpu_a100_il`, 1 A100, 16 CPUs, 64 GB, up to 24 h | RF-DETR Small, 12 epochs, then scores the test split |
| `ft-baseline` | `gpu_a100_il`, 1 A100, up to 2 h | Scores YOLOv8s Open Images on the same test split |

Timings are estimates until the first run measures them.

**6. Follow progress.**

```bash
squeue -u $USER -n ft-prepare,ft-train,ft-baseline
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
