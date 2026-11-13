# RF-DETR training pipeline

Fine-tunes RF-DETR on Open Images V7 and scores it against the YOLOv8s Open Images model the app already ships. The goal and rules are in [AGENTS.md](../AGENTS.md).

| File | Job |
| --- | --- |
| `classes/pilot.txt` | The 110 pilot classes. `Target = Source, Source` merges Open Images classes (e.g. Man/Woman/Boy/Girl into Person). |
| `classes/full.txt` | The full vocabulary for Phase 2: 595 classes, one per app category, named as in the app so every class exports to its own category. |
| `openimages.py` | Downloads Open Images metadata and images; writes `train/`, `valid/` and `test/` in rfdetr's COCO layout, plus `dataset.json`. `--reuse data/pilot` hard-links images an earlier dataset already has. |
| `train.py` | Fine-tunes the whole model and resumes automatically if re-run. |
| `warmstart.py` | Gives each class that also exists in COCO its pretrained COCO head row. Without it, rfdetr's resizing gives our first class COCO's unused slot, and the smoke test then never detected Person at all. With `train.py --start-from <run>` the whole network starts from an earlier run of ours instead (the Phase 2 run starts from the pilot): classes it knew keep their trained rows, the others take their COCO row or start fresh. |
| `checkpoints.py` | Reads a checkpoint's class count. Training (from the warm start), scoring and export build models with it, because rfdetr 1.11.2 otherwise cuts a head with more than 90 classes down to 90 and silently drops the rest. |
| `evaluate.py` + `oi_metric.py` | Open Images-style mAP@0.5. Classes are only scored on images where they were human-verified, group-of boxes count once, and merged classes are de-duplicated. Each result also holds a parent-aware score (`hierarchy`). |
| `hierarchy.py` | The Open Images class hierarchy for that second score: a child also counts as its parents (a Dog box is also an Animal box), as the Open Images Challenge scores. Ground truth goes up the tree, verified-absent labels down, and detections up, for both models alike. |
| `compare.py` | A Markdown report comparing two results class by class: overall scores, how many classes got better or worse, biggest gains and losses, weakest classes, with training and test counts so thin classes stand out. |
| `export.py` | Writes the app's ONNX file for the `rfdetr-oi` profile: boxes plus one logit per app category (615), with each trained class placed in its app category through the app's own Open Images name table. It checks the ONNX output against PyTorch and writes a `.json` summary next to it: every query the app could show (score at least 0.05, its lowest setting) must have a partner within tolerance, and the detections at 0.3 must be the same. Queries below 0.05 may differ, because the model picks its queries with a top-k that tiny numeric differences can reorder or swap at the cut-off. |
| `missing_labels.py` | Phase 3 switch, off by default (`train.py --unverified-weight W`): the "absent" part of the classification loss gets weight W for classes nobody verified on an image, and 0 for parents of a present class (a Dog box no longer teaches "not Animal"). Verified classes keep weight 1. Written against rfdetr 1.11.2's loss and refuses other versions |
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
| `resubmit` | Cancels the pilot chain's recorded jobs that are still queued or running, then submits again with `kit/submit.env` |
| `add` | Queues extra jobs next to the pilot chain without cancelling anything, e.g. `-Job full-speed,full-train` or `-Job report`. See below |
| `sync` | Only installs the uploaded code (and updates `.venv` when `requirements.txt` changed) |
| `fetch` | Downloads a finished run's `eval-test.json`, the baseline's, its `compare-baseline.md` and `rfdetr_openimages.onnx` (+ `.json`) into `runs\`, then installs the model into `models\` and next to the built app. It refuses a model whose ONNX check failed. `-Run <name>` picks the run (default `pilot-small`; `full-small` for Phase 2) |

`kit/submit.env` holds the submission settings in Git. It is set from the queue probe:

1. The data job runs as up to three resumable 30-minute parts in `dev_cpu_il`.
2. Then a 30-minute GPU smoke test runs in `dev_gpu_a100_il` (`kit/smoke.sbatch`). It trains two epochs on a 1,500-image slice, scores it, and writes `runs/gpu-smoke/throughput.json` with images per second and the estimated minutes per full epoch.
3. The baseline scoring also runs in `dev_gpu_a100_il`.
4. Finally, one 24-hour training job may start on `gpu_h100_il`, `gpu_h100` or `gpu_a100_il`, whichever is first. It only starts if the smoke test passed.

Slurm keeps a batch script exactly as it was when the job was queued, so `train.sbatch` and `smoke.sbatch` only hold the resource request and run `kit/train_job.sh` and `kit/smoke_job.sh`, which are read when the job starts. (The pilot's training job was queued before the export step existed and so never exported; that cannot happen again.) `kit/train.env`, or `kit/<run>.env` for a named run such as `kit/full-small.env` (epochs, batch size, the run to start from), is read at start too. Change it, then `-Action sync`, and a queued job picks it up without losing its place. A resumed run keeps the epoch count it started with, because the cosine schedule is sized from it. `TRAIN_PARTS` can split training into back-to-back jobs that resume, and a finished run cancels its own leftover parts. That only helps when waits depend on job length; on 2026-10-24 they depended on priority. The data job is skipped once `data/<dataset>/dataset.json` exists. `sinfo` is not permitted for this account, so `probe` is how to compare queues.

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

### Extra jobs next to the pilot

`-Action add` uses `kit/submit_extra.sh`. It records its jobs in `logs/extra.txt`, never in `logs/submitted.txt`, so `launch`, `resubmit` and the training job's own clean-up leave them alone, and it never cancels anything itself. A job that is still queued or running is not queued twice. If Slurm refuses a job for a per-user limit, nothing is queued and the script prints FrameTrail's own job count and the per-user limits.

The dev queues allow one running and at most three queued jobs per user ([bwHPC wiki](https://wiki.bwhpc.de/e/BwUniCluster3.0/Running_Jobs)), and this user account is shared with another project. On 2026-10-25 the first `add` queued four 30-minute `full-data` parts in `dev_cpu_il`; they filled that limit, so the export was refused (`QOSMaxSubmitJobPerUserLimit`). The extra jobs now run in `cpu_il` and leave the dev slots free.

| Job | Resources (from `kit/submit.env`) | What it does |
| --- | --- | --- |
| `smoke-model` | `cpu_il`, 4 CPUs, 16 GB, 30 min | Exports the GPU smoke test's 2-epoch checkpoint as `runs/gpu-smoke/rfdetr_openimages.onnx`. Its accuracy is meaningless; it lets the laptop check the `rfdetr-oi` profile on DirectML (`-Action fetch -Run gpu-smoke`) before the real model exists |
| `pilot-model` | `cpu_il`, 4 CPUs, 16 GB, 30 min | Exports `runs/pilot-small`'s best checkpoint as the app model, for runs whose training job did not export it (train 7911863 was submitted before the export step existed). Then `-Action fetch` |
| `full-data` | `cpu_il`, 16 CPUs, 32 GB, up to 3 h (a re-run resumes) | Builds `data/full` from `classes/full.txt`, hard-linking the images `data/pilot` already has. Dry run on 2026-10-25: 175,051 train / 6,584 valid / 16,788 test images, selected in 3.7 min with 5.2 GB memory. Estimated at most ~58 GB of images. Before downloading it checks this user's storage quota (`kit/space_check.sh`) and stops if 60 GB plus 100 GB of headroom are not free, so queued training keeps room for checkpoints |
| `full-baseline` | `cpu_il`, 16 CPUs, 32 GB, up to 10 h | Scores the app's YOLOv8s Open Images model on `data/full`'s 16,788 test images: the bar for Phase 2, measured without a GPU. Locally 1.1 s per image on 4 CPUs; not resumable, hence the long limit |
| `full-speed` | `dev_gpu_a100_il`, 1 A100, 30 min | The GPU smoke test for Phase 2: two short epochs on a 1,500-image slice of `data/full`, started from the pilot as the real run is, then scoring, measured speed (`runs/gpu-smoke-full/throughput.json`) and an export with its check |
| `full-train` | `gpu_h100_il`, `gpu_h100` or `gpu_a100_il`, 1 GPU, 16 CPUs, 64 GB, up to 24 h | The Phase 2 run (`runs/full-small`): RF-DETR Small on `data/full` from the pilot, epochs and settings in `kit/full-small.env`, then scoring, the report and the export. Queued with `full-speed`, it waits for the smoke test to pass. Queuing it again resumes an unfinished run |
| `report` | `cpu_il`, 4 CPUs, 16 GB, up to 1 h | Re-scores every finished run from its saved predictions (adding the parent-aware score; the flat score stays the same) and writes `runs/<run>/compare-baseline.md` against the YOLOv8s baseline on the same data. No model is loaded |

The full dataset is thin for some classes: 60 have fewer than 100 training images, and 61 have fewer than 10 test images (16 have none, so they cannot be scored). Container and Kitchenware have no boxes in any split and are left out.

**Follow progress** with `-Action status`. It only queries the FrameTrail job IDs recorded at submission, never the whole shared account.

**Results.** Two files hold the answer:

- `runs/pilot-small/eval-test.json`: our model's scores.
- `runs/baseline-yolov8s-oiv7-pilot/eval-test.json`: the baseline's scores.

Each holds `map50`, `map50_people_and_vehicles` and per-class AP. The training job also writes `runs/pilot-small/rfdetr_openimages.onnx`, the app-ready model, with its `.json` parity summary. Copy them back to the laptop (small files) or paste the summary lines from the logs.

If training stops at the time limit, resubmit only the training job and it resumes:

```bash
sbatch training/kit/train.sbatch
```

## Without the cluster: one rented GPU machine

The KIT account was lost on 2026-11-05, together with everything stored there (the pilot checkpoint, `data/full`, saved runs). What survives is the code, the pilot's scores and app model fetched to the laptop (`runs\pilot-small\`, `models\rfdetr_openimages.onnx`), and the numbers in AGENTS.md. `cloud/phase2.sh` runs the whole Phase 2 on **one Linux machine with an NVIDIA GPU**, with no Slurm. It works on an Azure NC-series VM or any GPU rental (RunPod, Lambda, ...):

```bash
git clone https://github.com/MogProgJ/FrameTrail.git && cd FrameTrail && git checkout claude/kind-brahmagupta-4q5cdd
tmux new -s train               # so it survives a closed laptop
bash training/cloud/phase2.sh   # setup, data, baseline, train, report, package; each stage skips finished work
```

Run it again after any interruption and it carries on (data downloads resume, training resumes from `last.ckpt`). Stages can be named: `bash training/cloud/phase2.sh data baseline`. **Billing.** You pay for every second the machine is rented and running, whether the GPU is busy or idle: the data download, scoring and any waiting cost the full hourly price. Stopping a machine ends the GPU charge but not the storage charge (RunPod lists $0.20 per GB-month for a stopped pod's disk, so 100 GB is about $20 a month; Vast.ai bills storage until the instance is destroyed), so **copy the results off, then destroy the machine** in the provider's console. `RUN_DEATH_SWITCH=1` makes the script run `poweroff` when it ends or fails, but on a rented container that may not end the billing; treat it as a convenience and still check the console. Prices and billing rules are from the providers' documentation, not tested.

Results end up in `~/frametrail-work/results/` (scores, the report, the app model and its check, the best checkpoint): **copy them off the machine before deleting it**, which is what was lost last time.

**Budget.** The `plan` stage measures the real speed of the machine on the real data (a 2-epoch test), then sets the number of epochs so that training fits `BUDGET_USD` at `PRICE_PER_HOUR`, with 2.35 h of the budget reserved for data, baseline, scoring and the test itself, and a hard time cap on the training stage. Example: `PRICE_PER_HOUR=1.39 BUDGET_USD=25 bash training/cloud/phase2.sh` on an A100 (the speed measured on the cluster, 55.6 images/s, gives 16 epochs of the full set, about $21 of training). The default training set is capped at 300 images per class (102,598 images, about 35 GB) instead of 600 (175,051, 60 GB): the common classes (person, car) lose images they hardly need, rare classes are limited by what exists anyway. Not measured whether that costs accuracy.

**Trying a free GPU first (Kaggle, Colab).** `bash training/cloud/speedtest.sh` checks any GPU session in 30-40 minutes: Python, internet, disk, memory, and the training speed, with a table of hours per epoch for each training-set size. On Kaggle set the Accelerator to a GPU and Internet on (phone verification), and use `FT_ROOT=/kaggle/temp/ft`. Kaggle limits (secondhand, check its docs): about 30 GPU hours a week, sessions of at most 12 hours, about 20 GB of persistent disk, a P100 or two T4s. The Session panel showed a real disk limit of 57.6 GiB (`df` reports the host's 967 GB), of which 21 GiB was used after setup (environment about 10 GB plus 6 GB of Open Images metadata), which leaves room for 13 GB of images but not 35 GB. Measured there on 2026-11-05: **12.7 images/s** on one T4 at batch size 8 (batch 16 runs out of the 15 GB GPU memory), 4.4 times slower than an A100, which makes 100 images per class (38,881 images) 0.94 h per epoch and 20 epochs 18.7 h, two sessions of at most 12 h and about 19 of the 30 weekly GPU hours. `cloud/kaggle_run.sh` is one such session: clone into `/kaggle/temp` (not `/kaggle/working`, which is saved as output and would carry 28,000 files), "Save Version" -> "Save & Run All" so it runs in the background, and for the next session add the previous version's output as an Input; it restores the checkpoint from `/kaggle/input/*/keep` and carries on (the restore and save logic is tested with a fake training stage; not yet run on Kaggle). Training-set sizes: 100 per class 38,881 images, 200 per class 72,660, 300 per class 102,598, 600 per class 175,051.

Needs about 100 GB of disk (data ~35 GB at the default cap, metadata ~6 GB, checkpoints), a GPU with 24 GB or more (it tries batch size 16, then 8 x 2), and python3.12 or newer. The settings are `kit/full-small.env`; without `runs/pilot-small` it trains from the official COCO weights instead of the pilot. The data selection is deterministic (seed 17), so a rebuilt `data/full` is the same set of images. Not measured off the cluster: download speed and the epoch time on the rented GPU.

## Round 3: fill in the missing labels (Kaggle)

**Why.** On the user's street footage the Phase 2 model misses most handbags, backpacks and umbrellas that YOLOX-S finds (footage check: 15%, 0% and 4% of YOLOX-S's boxes), although on Open Images test photos it scores well on them. Open Images leaves many such objects unlabelled, and training treated them as background. Round 3 adds the boxes YOLOX-S (the teacher) finds for classes **nobody verified on that image**, then trains the Phase 2 model 6 more epochs on the same 38,881 images. Human labels and human "absent" verdicts are never overridden.

**How the teacher is trusted.** `pseudo_labels.py measure` checks YOLOX-S against the human labels on images where a class was verified, per class and per score threshold. `fill` uses, per class, the lowest threshold whose precision is at least 80% with at least 15 checked boxes; classes that never reach it get nothing. Boxes smaller than 1% of the image side or overlapping an existing box (IoU above 0.6) are skipped. `train/_annotations.original.json` keeps the untouched labels; added boxes carry `oi_pseudo: 1` and the teacher's score. `audit` draws pictures (human boxes green, added orange) to look at. The validation and test splits are never changed, so scores stay comparable with Phase 2 and YOLOv8.

**Run it.** A Kaggle notebook with one cell (the same pattern as `kaggle_run.sh`):

```bash
%%bash
git clone --depth 1 --branch claude/kind-brahmagupta-4q5cdd https://github.com/MogProgJ/FrameTrail.git /kaggle/temp/FrameTrail
bash /kaggle/temp/FrameTrail/training/cloud/kaggle_round3.sh
```

Settings: Accelerator GPU T4, Internet on. **Input:** the Phase 2 notebook's Version 2 output (it holds `keep/full-small/checkpoint_best_total.pth`). Then "Save Version" -> "Save & Run All". One session does everything: data (about 16 min), teacher (CPU, about 1.5-2 h, an estimate from 7.5 images/s on the laptop's CPU), 6 epochs (about 5.2 h at Phase 2's 52 min per epoch), scoring, the comparison with Phase 2 and the app model: about 7.5 h in all, about 7 GPU hours. If a session stops early, run a new version with the stopped version's output added as a second Input; every stage resumes.

To save GPU hours, a first session with **no accelerator** and `ROUND3_STAGES="data teacher"` (put `export ROUND3_STAGES="data teacher"` before the `bash` line) does the teacher work on CPU; the GPU session then adds that output as an Input and skips the teacher run (it only re-applies the labels).

**Results:** download the single file `results-round3.zip` from the top of the version's Output tab (about 120 MB; the 136 MB checkpoint stays in `keep/` for later runs). The same files are under `keep/results-round3` (scores, `compare-phase2.md`, `teacher-measure.json`, `pseudo_labels.json` with what was added per class, the audit pictures, the app model). The log ends with mAP@0.5 and people-and-vehicles against Phase 2.

**What counts as a win** (all three):
1. Open Images test mAP@0.5 not clearly below Phase 2 (0.6877; within about 0.01), people and vehicles at least 0.76.
2. On the user's footage, the share of YOLOX-S's confident boxes the new model also finds rises clearly for handbags, backpacks and umbrellas (Phase 2: 15%, 0%, 4%; all objects 62%), without falling for people (87%) and cars (58%). Before installing, run the same check on the same five videos (listed in `output\footage-check-before-round3\videos.txt`):
   `powershell -ExecutionPolicy Bypass -File scripts\footage-check.ps1 -VideoList output\footage-check-before-round3\videos.txt -Models round3=<path to the new onnx>`
   Combined scores 100% there by construction (it contains YOLOX-S); it is the ceiling, not the target.
3. Reviewing one analysis of own footage shows no new kind of false box.

Install with `training\cloud\install-model.ps1 -From <download>` as below (it keeps the Phase 2 model as a backup).

Tested locally on 2026-11-07 on a small slice (1,922 images): the teacher's port gives the app's detections (27 of 27 boxes, within 0.003 px), measuring, filling (146 boxes added to 801 images) and the audit pictures work, and `kaggle_round3.sh` ran end to end with fake data and training stages, as a CPU-only session (data, teacher) followed by a GPU session that restored its teacher results and trained. Not yet run on Kaggle.

## Round 4: Open Images plus COCO, partial-label loss (Kaggle)

**Why.** Yardstick A (COCO val2017, every object of 80 types labelled; `coco_yardstick.py`, `runs\yardstick-a\report.md`) shows where round 3 stands on everyday objects: AP@0.5 0.497 against YOLOX-S's 0.585, and at equal strictness (77% of boxes right) it finds 44% of the objects against 56%. The gap is largest for kitchen and table objects (cup 0.17 against 0.56, bowl 0.26/0.59, bottle 0.28/0.57, dining table 0.12/0.46) and for small objects (15% found against 33%). The earlier diagnosis says why: Open Images leaves most such objects unlabelled, and training read "unlabelled" as "absent". Round 4 adds COCO train2017, where every object of the 80 types is labelled, and trains with a loss that knows what each photo vouches for.

**What changes.** `mix_coco.py` puts 117,216 COCO photos (844,099 boxes; numbers from a dry run on the real annotations) next to the 38,881 Open Images photos, which are stored at 640 px (COCO's size) so both fit on Kaggle's disk. Each COCO box goes to the class that means the same thing (cow to Cattle, dining table to Table, 15 such names); cup gets a class of its own (596 classes), because Open Images only has Coffee cup and Mug. Per photo the annotations record what is verified present, verified absent and unknown; `train.py --unverified-weight 0.25` (`missing_labels.py`) then pushes a class towards "absent" fully where a photo vouches for it, not at all where it is unknown (Van on a COCO photo with a car, anything COCO marks as a crowd, Cup on an Open Images photo with a mug), and at a quarter strength everywhere else. Two COCO types do not line up with one class: "tv" lumps televisions and monitors, so its boxes are not used; our Table is wider than "dining table", so COCO never says "no Table". No teacher model is used: COCO's human labels replace round 3's YOLOX-S boxes. Training continues the round 3 checkpoint for 6 epochs at the full learning rate (`kit/round4.env`).

**Success criteria, fixed before the run** (2026-11-12):
1. **A (COCO val2017), the point of the round.** At YOLOX-S's share of boxes right (77%) the model finds clearly more objects than round 3's 44%: at least 52% counts as "the recipe works", 56% or more (YOLOX-S's level) meets the plan's A criterion. AP@0.5 is reported next to it (round 3 0.497, YOLOX-S 0.585), with the by-size shares; small objects are expected to stay the weakest and decide the model-size question.
2. **B (Open Images test) is not paid for it:** mAP@0.5 at least 0.675 (round 3: 0.6855), people and vehicles at least 0.76.
3. **C (video)** is not judged by agreement with YOLOX-S. The 12 practice clips are only looked at for new kinds of error; the unopened clips are used once a model meets 1 and 2.
The stock COCO-pretrained RF-DETR Small is scored on A in the same session: it shows what this architecture reaches on the 80 types, so the result can be read as "how much of that did we recover while keeping 596 classes".

**Run it.** A Kaggle notebook with one cell:

```bash
%%bash
git clone --depth 1 --branch claude/kind-brahmagupta-4q5cdd https://github.com/MogProgJ/FrameTrail.git /kaggle/temp/FrameTrail
bash /kaggle/temp/FrameTrail/training/cloud/kaggle_round4.sh
```

Settings: Accelerator GPU T4, Internet on. **Input:** the round 3 notebook's final version (it holds `keep/round3/checkpoint_best_total.pth`); for every later session also this notebook's latest version. Then "Save Version" -> "Save & Run All". Setup and data take 1 h 19 min per session (measured on 2026-11-12: environment 12 min, Open Images 27 min, shrinking and COCO's 117,215 photos 40 min; the shrunk Open Images training photos are 3.0 GB, down from 11.7 GB). Estimates, not measured: one epoch about 3.1 h (156,000 photos at round 3's speed), so 6 epochs are about 19 GPU hours over two or three sessions, about 22-24 hours of the weekly 30 with setup and scoring. The script measures each epoch and stops training at an epoch boundary when the next one would not fit in the 12-hour session, so no partial epoch is lost; the log then says to start the next session. Disk, also an estimate: about 21 GB environment and metadata, 7 GB Open Images validation and test photos, 3 GB shrunk training photos, 18 GB COCO, against Kaggle's 57.6 GiB; the log prints the free space after the data stage.

Right after the environment is built and before any data is downloaded, the `check` stage runs the pipeline's tests in Kaggle's environment (the loss against rfdetr itself), so a failure costs about 12 minutes. The first session (2026-11-12) stopped at this stage after the data, 79 minutes in, without the tests having run: `python -m unittest tests.test_...` could not import them, because `tests/` has no `__init__.py` and Python then prefers any installed package named `tests` (reproduced locally with such a package on the path). The stage now runs them from inside `tests/` by file name. During training the loss also checks, on the first 2,000 images, that the trainer's image ids are the annotation file's, and stops with a clear message if not: otherwise the weights would silently go to the wrong photos.

**Measured in the first full session (2026-11-12/13, 7.4 h).** Setup 10 min, Open Images data 8 min, COCO 15 min (the downloads were three times faster than the day before), the stock model 4 min, then two epochs of 3.35 h and 3.33 h each. With 3.7 h left the third epoch (about 3.8 h with its margin) did not fit, so a session trains two epochs and the round needs three sessions. The stock COCO-pretrained RF-DETR Small on yardstick A: AP@0.5 0.725, 69% of the objects found with 76% of its boxes right at 0.35 (YOLOX-S 56% at 77%; round 3 44% at that strictness); small 48%, medium 79%, large 89%.

**Interim scores (`interim` stage).** rfdetr's validation score on the Open Images validation photos fell from round 3's 0.53 (mAP@0.5) to 0.416 after epoch 1 and 0.395 after epoch 2, and its recall ceiling (mAR@500) from 0.787 to 0.734 and 0.718. That score counts a box on an unlabelled object as wrong, so finding more everyday objects lowers it, but a lower recall ceiling is not explained by that alone. Whether yardstick B fell is unknown until it is measured, so before more epochs are trained the saved checkpoints are scored without training:

```bash
%%bash
git clone --depth 1 --branch claude/kind-brahmagupta-4q5cdd https://github.com/MogProgJ/FrameTrail.git /kaggle/temp/FrameTrail
ROUND4_STAGES="check interim" bash /kaggle/temp/FrameTrail/training/cloud/kaggle_round4.sh
```

Inputs: round 3's output and the round 4 version that trained. It scores round 3 on A through rfdetr (to compare like with like), then round 4's best-by-validation checkpoint (epoch 1) and its newest (`last.ckpt`, epoch 2, made scorable by `checkpoints.py averaged`, which takes the averaged weights the trainer validates with) on A and B. Estimate: 1-1.5 h with a GPU. Results: `interim-round4.zip` at the top of the Output tab (the A table, each B score with a class-by-class comparison against round 3, the A prediction files). A training session that stops unfinished now scores its newest checkpoint the same way when at least 100 minutes of the session are left.

Open until those numbers exist: `train_job.sh` scores and exports `checkpoint_best_total.pth`, which rfdetr picks by its validation score. Here that is epoch 1, so as things stand the final model would not be the 6-epoch one.

**Results:** `results-round4.zip` at the top of the final version's Output tab. On the laptop:

```powershell
# yardstick A for the new model, with the files already scored for YOLOX-S and round 3 (about 35 min on the CPU)
python training\calibrate.py predict --model <unzipped>\rfdetr_openimages.onnx --images data\coco\val2017 --out runs\yardstick-a\round4.jsonl
python training\coco_yardstick.py score --annotations data\coco\annotations\instances_val2017.json --model yolox-s=runs\yardstick-a\yolox-s.jsonl --model round4=runs\yardstick-a\round4.jsonl --model round3=runs\yardstick-a\round3.jsonl --model stock-rfdetr-small=<unzipped>\yardstick-stock-rfdetr-small.jsonl --out runs\yardstick-a\report-round4.md
```

(`calibrate.py predict` needs onnxruntime; the system Python here has none, the session's scratch environment does.)

**Known limits of this round.** Checkpoints are still picked by rfdetr's validation score on Open Images validation photos, which counts a correctly found but unlabelled object as an error; all epochs share that bias, so it should not change which epoch wins, but it is not measured (the first two epochs suggest it does matter: see "Interim scores"). Cup and Mug can now both fire on one mug; the app needs the same hiding rule it has for wheel and bicycle wheel before this model is installed. The 0.25 weight and the 3:1 share of COCO photos are judgment calls, to be changed only on yardstick results.

Tested locally on 2026-11-12: 87 Python tests pass (mixing, the class table against the real 595-class list: all 80 COCO types map to 80 distinct classes; the loss weights with PyTorch), a dry run on the real COCO train annotations, and `kaggle_round4.sh` end to end with stand-in data and a fake trainer as two sessions (3 epochs, stop at the epoch boundary, resume, finish, results zip). Not run: anything that needs rfdetr or a GPU (the real loss, the stock model's prediction, scoring and export with 596 classes); the `check` stage covers the first of these at the start of the Kaggle session.

## Use a trained model in the app

**From Kaggle or a rented machine:** download the `results` folder (on Kaggle: the version's Output tab, `keep/results`, or the whole output as a zip), then from the FrameTrail folder run
`powershell -ExecutionPolicy Bypass -File training\cloud\install-model.ps1 -From "$HOME\Downloads"` (a folder or a .zip). It installs the model only if its ONNX check passed, keeps the model installed before as `models\rfdetr_openimages-<run>.onnx` (the app loads one trained Open Images model at a time), and saves the scores in `runs\full-small\`.

**From the cluster (history):** run `-Action fetch` from the laptop. It downloads `runs/<run>/rfdetr_openimages.onnx` (about 115 MB for RF-DETR Small) and puts it in `models\` and in `build\windows-msvc\Release\models\`, where the app looks. Later builds copy it from `models\` too. Start FrameTrail and pick **RF-DETR · Open Images (trained)**. From the command line: `--model-type rfdetr-oi`.

The app accepts the file because of its metadata (profile `rfdetr-oi`, the 615-category vocabulary and the 512 px preprocessing), not a pinned checksum, so every retrained model drops in the same way. Classes the model was not trained on are never reported. Saved runs, tracking, appearance counting and CSV export work as with the other models, because classes keep the app's usual category IDs.

Checked on 2026-10-24 with a small test checkpoint: the app's own detector code (built on Linux against ONNX Runtime 1.30) loaded the export and returned the same detections as rfdetr. Files with a wrong profile or preprocessing were refused, and saved runs, new and old, opened correctly. The Windows build then passed all 37 checks on the laptop. The DirectML GPU path with this profile is still untested.

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

## Score calibration (no training)

mAP ranks boxes within one class, so it cannot tell whether a class's correct boxes clear the app's confidence setting. They often do not: the trained model localises nearly every object YOLOX-S finds on the test clips (a box at the right place exists for 94% to 100% per class), but gives most household objects a score of 0.1 to 0.3. `training/calibrate.py` fits one curve per class on human-verified **validation** images, so that a score means "chance this box is right" for every class; the app applies it when the table sits next to the model (`docs/DETECTION.md`).

```
python training/calibrate.py predict --model models/rfdetr_openimages.onnx --images data/full/valid --out runs/round3/calibration-valid.jsonl
python training/calibrate.py fit --predictions runs/round3/calibration-valid.jsonl --annotations data/full/valid/_annotations.coco.json --out models/rfdetr_openimages.calibration.csv
```

`predict` runs the app's own ONNX model with the app's preprocessing and decoding (onnxruntime, numpy, Pillow; resumable; about 1 s per image on a laptop CPU). `fit` uses the evaluator's rule (a class counts only on images where it was verified), pulls classes with little evidence towards the curve of all classes, and writes the table, a report (`.md`) with a check per class, and the numbers (`.json`). Give `--check-predictions` and `--check-annotations` to test the curves on images that were not used for the fit. Copy the table next to both copies of the model (`models\` and `build\windows-msvc\Release\models\`). Refit after every retraining: a table belongs to one model.

Local trial on 2026-11-10 (round 3 model, 19 street classes, 1,121 validation photos for the fit, 966 others for the check): calibrated scores of 0.5 to 0.7 were right 75% of the time and 0.7 and above 94%, where raw scores of 0.35 to 0.5 were already right 83%. On the twelve test clips a calibrated setting of 0.5 finds 71% of YOLOX-S's confident boxes of those classes instead of 65%, and 62 of 80 randomly drawn newly shown boxes were right by eye. Numbers and tools: `output\calibration-local\`.

Full fit on 2026-11-11 (556 classes, 6,584 validation photos, `output\calibration-full\`): honest on held-back photos, but on the clips it matches a lower confidence setting rather than beating it (calibrated 0.5: 72% found at 79% agreement and 34 boxes per frame; raw 0.27: 72%, 77%, 22). Not installed. Use the fit report to see which classes a model under-scores; do not expect it to replace training.

## Known limits

- Open Images labels are incomplete. Training treats unlabeled objects as background, the same as public Open Images detectors do. Evaluation corrects for this; training does so only in round 3, and only where YOLOX-S knows the class (its 80 COCO classes).
- Group-of boxes, which cover a crowd of the same objects, are trained as ordinary boxes.
- Merging Man/Woman/Boy/Girl into Person removes near-duplicate boxes at IoU 0.7. An image verified to contain no Man is treated as verified for Person.
