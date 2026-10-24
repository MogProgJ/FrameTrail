# FrameTrail — working agreement

Read this first in every session. It is the single source of truth for direction, rules and status. Keep it short and current: update **Status** and **Decision log** when something real changes; do not add history essays, receipts or handoff files.

## What FrameTrail is

A native Windows desktop app (C++20, Qt, FFmpeg, ONNX Runtime, SQLite) that analyses images, video files and a webcam. It detects objects, tracks them over time, records when each appearance starts and ends, counts line crossings, and exports results. Private, single-user project. It will not be sold or shared.

## The goal

**One RF-DETR model that recognises about 600 everyday object categories well enough to be the app's main detector.**

Concretely, the first target is a fine-tuned RF-DETR that:

1. Covers the Open Images everyday vocabulary (pilot: about 100 classes, then about 600).
2. Beats the YOLOv8 Open Images model already in the app on the same held-out Open Images test images (Open Images-style mAP@0.5).
3. Stays at least as good as today on people and vehicles.
4. Runs inside FrameTrail (ONNX, GPU via DirectML, CPU fallback).

"Anything you throw at it" beyond the trained vocabulary is a later, separate open-vocabulary mode. It is not a requirement for the main model.

## Strategy in one paragraph

Train the whole RF-DETR model (not single classifier rows) on large public datasets (thousands of images per class), measure with a standard metric on large held-out sets, and iterate in a few meaningful GPU runs instead of many tiny diagnostics. Open Images V7 first, because its 600-class vocabulary already matches the app. Later, add Objects365/LVIS for rare classes, fill missing labels with a teacher model, and build a small test set from the user's own videos.

## Phases

| Phase | What | Done when |
| --- | --- | --- |
| 0. Pipeline | Open Images → RF-DETR COCO dataset, training wrapper, Open Images-style evaluator, KIT job scripts, local CPU smoke test | Smoke test trains and evaluates end to end |
| 1. Pilot | ~100 everyday classes, capped images per class, RF-DETR Small, one A100 | Clear mAP above the YOLOv8 Open Images baseline on the pilot classes |
| 2. Full vocabulary | ~600 classes, capped per class, bigger model or longer run | Goal points 2–3 met on the full test set |
| 3. Next level | Missing-label handling (verified-label loss masking or teacher pseudo-labels), Objects365/LVIS, own-video test set | Measured gain on rare classes and own footage |
| 4. App | Loading trained models is done (`rfdetr-oi` profile). Left: frame-rate sampling for long videos, class-flicker-tolerant tracking, DirectML check of the new profile | New model is the app default |

## Rules that keep us on track

- **Measure, don't argue.** Every training run ends with `training/evaluate.py` metrics on held-out test images. A claim about model quality needs a metrics file behind it.
- **Use public splits.** Train on Open Images *train*, select checkpoints on Open Images *validation*, report on Open Images *test*. Never train on validation or test images.
- **Respect missing labels in evaluation.** Open Images labels are not exhaustive. The evaluator only scores a class on images where that class was human-verified (present or absent). Detections of unverified classes are ignored, not counted as false positives.
- **Big levers first.** More and better data, full fine-tuning and a bigger model before loss tweaks. Do not hand-curate dozens of photos or sweep tiny hyperparameter grids.
- **Lightweight provenance.** Each run directory holds its config, dataset manifest, git commit, logs, checkpoints and metrics. That is enough; no receipts, seals or authorization files.
- **Data and weights stay out of Git** (`data/`, `runs/`, `*.pth`, `*.onnx` are ignored). Only code, configs, class lists and small result summaries are committed.
- **Keep the app working.** Do not break the existing analysis, save, export or playback flow when integrating a new model. YOLOX-S stays the default until a new model clearly beats it on the user's footage.
- **Don't invent facts.** If something is not verified (cluster limits, timings, accuracy), say so and check it. Write estimates as estimates.

## Cluster (KIT bwUniCluster 3.0)

- Host `uc3.scc.kit.edu`, user `ka_udxvl`, workspace via `$(ws_find frametrail)`. Partitions used before: `cpu_il` (data jobs) and `gpu_a100_il` (training). Python module `devel/miniforge/25.3.1-python-3.12`. Compute nodes have had outbound internet in earlier jobs.
- Access is key-based SSH from the user's Windows laptop (bwIDM Interactive key, unlocked in the Windows agent for about 8 hours after OTP). Cloud sessions cannot reach the cluster (no SSH route, and the key stays on the laptop). Submissions run from the laptop, by the user or by a Claude session on that machine, via `training/kit/launch-from-windows.ps1`. Never ask for, copy or store credentials or keys. Before anything is submitted, state what it will use (GPUs, hours, disk).
- The account is shared with another project ("Carrington Event"). Only touch FrameTrail jobs and files: never inspect, cancel or modify other jobs, and never use account-wide or wildcard job commands.
- `sinfo` is denied for this account. Use `-Action probe` (read-only `sbatch --test-only`) to compare queues. On 2026-10-24, waits were priority-bound: `cpu_il` was estimated at about 3 days and `gpu_a100_il` at about 2 weeks regardless of job length, `gpu_h100_il` at about 6 days, and the dev queues (30 min) started at once. MI300 nodes need a ROCm build of PyTorch; not used.

## Communication preferences (from the user)

- Plain language in chat. Say what changed, what it means and what is next. Keep formulas and long details in files.
- End every reply with the single best concrete next step and why it comes next.
- Work autonomously on local tasks; ask only for real decisions, credentials or cluster submission.

## Repository map

| Path | Contents |
| --- | --- |
| `apps/`, `src/`, `include/` | Native app, CLI and core library |
| `tests/` | Native checks (CTest) and Python tool tests |
| `scripts/` | Windows build, dependency, packaging and profiling scripts |
| `dependencies/` | Pinned external artifact manifests and the 615-label app vocabulary |
| `training/` | Model pipeline: dataset prep, training, evaluation, export, KIT jobs |
| `docs/` | App reference docs (architecture, development, detection, tracking, saved runs, GPU, camera, packaging) |

Trained models reach the app through `training/export.py` and the `rfdetr-oi` profile ("RF-DETR · Open Images (trained)", file `models/rfdetr_openimages.onnx`). Exports keep the app's 615 category IDs, so saved runs, tracking and CSV export are unchanged. A class outside that vocabulary (for example from Objects365) would first need a new app category.

## Status

- 2026-10-24: Strategy reset. Removed the billboard-only research track and its archive (recoverable from commit `95b9ef23`).
- 2026-10-24: Phase 0 done. `training/` builds Open Images datasets, trains with resume, and scores with the Open Images-style evaluator against the YOLOv8s baseline. The local CPU smoke test (4 classes, 1 epoch) ran end to end. The pilot dry run on real metadata selects 49,418 train / 1,954 valid / 4,774 test images for 110 classes. Next: the user runs `training/kit/setup.sh` and `submit_pilot.sh` on KIT (see `training/README.md`).
- 2026-10-24: Pilot submitted on KIT: prepare 7911071, train 7911072, baseline 7911073. The environment is set up in `$(ws_find frametrail)/rf`, and the workspace now has 30 days and 2 extensions left. Slurm's estimated starts were 2026-10-27 (data) and 2026-11-08 (GPU). The probe showed priority-bound waits, so the plan changed to: data in dev CPU parts, a dev GPU smoke test that measures speed, the baseline in dev GPU, then one 24 h training job on H100 or A100 (`training/kit/submit.env`). Next: `-Action resubmit`.
- 2026-10-24: The original data job 7911071 started far earlier than Slurm's estimate and built `data/pilot`. Resubmitted the rest: baseline 7911861 and smoke 7911862 (dev_gpu_a100_il, estimated today), then train 7911863 (estimated 2026-10-30 on gpu_h100_il; it waits for the smoke test). Next: `-Action status` once the smoke test has run; set `train.env` epochs from its measured speed.
- 2026-10-24: Baseline YOLOv8s-oiv7 on the pilot test split (4,774 images, 110 classes): mAP@0.5 **0.5439**, people and vehicles **0.6241** (`runs/baseline-yolov8s-oiv7-pilot/eval-test.json`). This is the bar for Phase 1. The GPU smoke test passed on an A100 at 62.5 images/s, about 13 min per pilot epoch. Train 7911863 is set to 50 epochs with a cosine schedule (estimate: 11–13 h on an A100). Next: wait for it to run, then compare `runs/pilot-small/eval-test.json` with the baseline.
- 2026-10-24: Train 7911863 still pending (Priority). While it waits: added `training/export.py` and the app profile `rfdetr-oi`. The training job now also writes `runs/pilot-small/rfdetr_openimages.onnx`. Verified on Linux with a test checkpoint: the app's detector code gives the same detections as rfdetr, rejects mismatched files, and saved runs (new and old) open. Not yet built or tested on Windows/DirectML.
- 2026-10-24: Windows build with the new profile: all 37 checks pass (`scripts/build.ps1`). `-Action fetch` downloads a finished run's scores and installs its model next to the app. DirectML with the new profile is still untested (needs a GPU build and a trained model). Next: wait for train 7911863, then `-Action fetch`.
- 2026-10-24: App redesign stage 1 (look): Windows 11 dark theme with the system accent, Fluent icons, navigation pane, page headers, new video canvas and detection labels. The desktop tests pass on Linux (Qt 6.11.2 from conda-forge, offscreen). Next stages: shared media across sections, Home with recent files, seekable timeline, grouped analysis results, Playback folded into Analysis; then settings and a command palette.
- 2026-10-24: User found stage 1 too similar to the old app. Stage 2 changed structure and workflow: icon rail with Home, a Home start page (drop zone, tool cards, recent files, detector card), a status bar, a seekable Preview timeline (new `PreviewSession` start time, tested), an "In view" summary, Analysis chips per object type, an appearance timeline chart and highlighted thumbnails, and Analysis/Playback picking up the Preview video. Desktop and preview tests pass on Linux; the Windows build is the user's check.
- 2026-10-24: App stage 3: ambient glow around the video, an activity strip in the Preview timeline, focus on one object type from "In view", PNG snapshots with overlays (Ctrl+S, Pictures\FrameTrail) with a toast, and fades between sections. Fixed a stage-2 slip that commented out the rail painter (rail showed text only). Old annotation tooling reviewed (removed in `f38d8086`, recoverable): not revived; see Decision log.

## Decision log

- 2026-10-24: Switch from single-row billboard fine-tuning to full fine-tuning on Open Images. Reason: the largest earlier training set was 281 photos, while Open Images offers about 1.7M training images. Private use only, so public dataset licences are acceptable for training.
- 2026-10-24: Pilot uses RF-DETR Small (512 px), the size already integrated in the app, and rfdetr 1.11.2, the version previously used on KIT.
- 2026-10-24: Warm-start the classification head by class name (`training/warmstart.py`). rfdetr's default resizing gave our first class COCO's unused slot: in the smoke test, Person had AP 0.00 without the warm start and 0.90 with it.
- 2026-10-24: The evaluator applies class-wise NMS (IoU 0.7) after mapping, so a baseline predicting Man and Person on one person is not double-penalised.
- 2026-10-24: Train with a cosine learning-rate schedule (`train.py --lr-scheduler`, default). rfdetr's default "step" schedule only lowers the rate after 100 epochs, so a shorter run would never decay. Pilot length 50 epochs, sized from the measured smoke-test speed to fit one 24 h job with margin.
- 2026-10-24: Bring trained models into the app in the app's existing 615-category layout (`rfdetr-oi`), not with a per-model vocabulary. All 110 pilot classes map to distinct app categories through the app's own Open Images table, and saved runs, tracking and exports depend on those IDs. The profile is identified by metadata instead of a pinned checksum, so retrained models drop in.
- 2026-10-24: Desktop design follows Windows 11 (Fluent 2) on Qt Widgets with Fusion plus one stylesheet built from tokens in `apps/desktop/theme.hpp`. Icons are Fluent UI System Icons (MIT) compiled in as vector paths (`scripts/generate-icons.py`), so no Qt SVG module or image assets are needed. Object names that tests use stay unchanged.
- 2026-10-24: The old annotators are not reused as-is. The RF-DETR (COCO) pre-labeller and browser editor never produced a finished, measured label set (0 of 60 photos passed whole-image review), and the October 22 "assistant review" boxes were drawn and checked by the same AI, so they are not ground truth. Labels come from Open Images; missing labels are filled later by a measured teacher model; a small own-footage test set is the one place for model-suggested, human-confirmed labels.
- 2026-10-24: The pilot trains with the standard loss and treats unlabeled objects as background, as public Open Images detectors do. Missing-label handling is a Phase 3 improvement, decided by measurement.
