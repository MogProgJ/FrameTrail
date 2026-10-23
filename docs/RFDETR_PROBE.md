# RF-DETR Small: isolated CPU mechanics probe

Verified locally on 7 October 2026 (Europe/Berlin). The desktop app remains native
C++; Python is an offline tool, not a new shipped runtime. The user approved this
bounded experiment, not model adoption, substantial training or a GUI redesign.

Subsequent module: [RF-DETR-assisted annotation review](RFDETR_ANNOTATION.md) now
uses this verified export for 318 unreviewed suggestions on all 60 existing photos.
It does not change the CPU probe's acceptance scope or approve training/adoption.

## Outcome in plain language

We obtained the official pretrained Small weights, ran six existing photographs,
and exported a separate ONNX model. Its CPU detections agree with the Python model
on these inputs. The weights are usable for this experiment, but RF-DETR is **not
yet selectable in the app**, has not been fine-tuned by us, and has not proved an
accuracy improvement. The current app models and saved-analysis workflow are
unchanged. No new KIT job or photograph download was needed.

Open `output/rfdetr-probe/cpu-v3/comparison.html` in your normal browser for the
read-only three-column preview. Yellow boxes are predictions, not reviewed labels.
Do not copy them into the training dataset as approved annotations. Your
`editor-simple-v3.html` annotation correction page remains separate.

## Reproducibility and evidence

- Isolated environment: `.deps/rfdetr-probe-cpu`; Python 3.12.14,
  PyTorch 2.8.0+cpu, torchvision 0.23.0+cpu, RF-DETR 1.11.2,
  ONNX 1.19.1, ONNX Runtime 1.30.0, NumPy 2.2.6 and Pillow 12.3.0.
  Complete resolved packages and pip acquisition receipt are saved with the run.
- [Publisher release](https://pypi.org/project/rfdetr/1.11.2/) and pinned source
  commit `7433d5919d0f7e72cc6cb78663e0a731afd499e0`. The installed RF-DETR wheel
  SHA256 matches `2f23589567123b59302f1cfa9d14d23630f9f583ee6f3468c5891e33fb103b2a`.
- [Publisher Small checkpoint definition](https://github.com/roboflow/rf-detr/blob/7433d5919d0f7e72cc6cb78663e0a731afd499e0/src/rfdetr/assets/model_weights.py):
  `https://storage.googleapis.com/rfdetr/small_coco/checkpoint_best_regular.pth`.
  Exact download: 386,045,550 bytes, explicit 400 MiB cap. Publisher MD5:
  `fb37061c1af7bace359c91b723a8d5c1`; local SHA256:
  `d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33`.
  Stored separately in `.deps/rfdetr-probe-assets`, with `acquisition.json`.
  MD5 is an integrity check, not a cryptographic authenticity guarantee.
- Completed experiment: `output/rfdetr-probe/cpu-v3/experiment.json`, with
  checkpoint, original-input, environment, native-baseline and source identities.
  Source snapshots, normalized inputs and raw PyTorch tensors are retained.
- Static float32 ONNX: `cpu-v3/onnx/rfdetr-small.onnx`, 114,434,018 bytes;
  SHA256 `a7d8e54b0e8aebc67c0de798f0e8951f9566d82e0ffa0a9cd4b4a22a3138d46d`.
  ONNX checker passed; CPUExecutionProvider was used.

All returned detections above 0.35 were checked bidirectionally by class, box
and score against the SDK. Acceptance limits: box IoU >= 0.98 and score delta
<= 0.003. Observed worst IoU was 0.9996729 and worst score delta 0.0003576.
There were 42 predictions in each RF path, including 24 above 0.55 (48 directional
strong matches). These are numerical-agreement counts, **not correct-object counts**.

Positionwise raw-query equivalence did **not** pass: raw box deltas reached
0.49038 and logit deltas 3.87493. Low-confidence query arrays differ; query order
is not an object identity. Disabling ONNX graph optimizations did not eliminate
all raw differences. The acceptance rule therefore checks the decoded prediction
sets, including the full returned 0.35-threshold set, while retaining raw deltas
and a false raw-tolerance flag. Equivalence on other inputs remains unproven.

Historical failed results are preserved. `cpu-v1` hit an incorrect interpretation
of the native CLI's blank `Fallback:` field (fixed with a regression test).
`cpu-v2` exported successfully but failed strict positionwise raw-array tolerance.
`cpu-v3` records the explicitly scoped decoded-output acceptance above; failures
were not erased or relabelled as successful runs.

Six RF ONNX CPU forward timings were approximately 360–392 ms, four CPU threads,
one timed pass per image after warmup. They exclude file decoding/preprocessing/
postprocessing and are not desktop end-to-end FPS. Native baseline wall times
include process startup/model load and are not directly comparable. No GPU,
DirectML, sustained-memory, camera, tracking or full-video benchmark was performed.

## Frozen probe contract

Input `input`: float32 `[1,3,512,512]`, RGB; bilinear tensor resize with
`antialias=False`, no letterboxing; ImageNet mean/std normalization. Outputs bind
by exact names: `dets` `[1,300,4]` normalized cx/cy/width/height; `labels`
`[1,300,91]` raw logits. Sigmoid and top-300 query/class pairs, no YOLO-style NMS.

The official pretrained model uses 80 COCO categories at sparse raw slots 1–90,
mapped explicitly to existing canonical IDs 0–79. Slot 90 is toothbrush, not
background. Gaps and slot 0 are not application classes. This is **not** the
597-category broad Open Images profile; fox and bracelet are not covered by this
COCO model. Never rename the export as `small` or `openimages` to bypass native
profile checks. Probe-only metadata does not register a production model.

## Commands — Windows PowerShell only

Setup, acquisition and the first probe have already completed; do not repeat them
unless intentionally reproducing. Setup safely reuses a verified environment,
and acquisition reuses the receipted checkpoint without another download.

```powershell
Set-Location 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskBasePython = 'C:\Users\nazee\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& .\scripts\setup-rfdetr-probe.ps1 -Python $taskBasePython
$taskProbePython = '.\.deps\rfdetr-probe-cpu\Scripts\python.exe'
& $taskProbePython -B scripts\probe-rfdetr.py acquire
& $taskProbePython -B scripts\probe-rfdetr.py contract

# Intentional rerun only: use a NEW results directory; existing runs are preserved.
& $taskProbePython -B scripts\probe-rfdetr.py run `
  --manifest output\kit-results\7450934\photo-pilot-7449188-first60\manifest.json `
  --output output\rfdetr-probe\cpu-v4 --count 6 `
  --baseline-cli out\FrameTrail-0.12.0-win64-preview\frametrail.exe
& $taskProbePython -B scripts\review-rfdetr-probe.py --run output\rfdetr-probe\cpu-v4

# Open the existing completed comparison; this does not run inference or training.
Start-Process '.\output\rfdetr-probe\cpu-v3\comparison.html'
```

There are no Linux/KIT commands for this completed local experiment. Do not copy
the Windows CPU environment onto the cluster. A future RF CUDA environment/job
needs its own pinned preparation and actual Slurm/CUDA evidence.

## Next gates, in order

1. Finish and save the user's first-60 annotation corrections. Accepted visual
   audits are not complete geometric labels, rights approval or a training release.
   Unsupported observations such as bracelet remain separate from frozen targets.
2. Freeze a manageable everyday-object scope and annotation policy, then obtain
   independent, fully labelled real-world evaluation inputs. The six publisher-train
   photos above are not that independent test; the old smoke test remains untouched.
3. Evaluate RF-DETR against unchanged baselines on common classes, separately
   reporting lost vocabulary coverage, per-class/domain errors and end-to-end cost.
   Only then decide whether its benefit warrants a new native two-output decoder,
   profile registration, compatible saved-run persistence and DirectML checks.
4. Expand reviewed data in bounded batches, assisted by model suggestions and
   human/sample QC. Corrections do not automatically train an annotation system.
   Validate any proposed automation's missed-object and wrong-box rates before
   allowing it to reduce review; no fixed confidence score establishes completeness.
5. Fine-tune on KIT only after the reviewed release/splits/evaluation gates pass.
   Export and re-evaluate the resulting weights before any app adoption.

All 100 Python tooling tests passed, including 19 RF probe/comparison checks.
The existing annotation-editor pure JavaScript/payload checks passed. Setup syntax,
safe environment reuse, dependency consistency, original-data identities and both
native baseline model identities were checked. The comparison's static output is
tested; browser rendering was not verified. No C++ code changed or build was needed.

The checkpoint and successful export establish that this model can be acquired
and exercised in our offline tooling. They do not settle whether it is the best
model for FrameTrail, or whether it can outperform our current baselines.
