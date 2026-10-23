# Latest handoff — 24 October 2026

Read [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) and [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md) first. The code in the main tree now includes the latest single-window desktop and Quick Guide continuation. Full findings and original versioned handoffs are archived under [research/](research/README.md). The sections below are preserved historical context and do not supersede the latest handoff.

---

# FrameTrail continuation handoff

Updated: 8 October 2026 (Europe/Berlin). Read this first when continuing in a new chat. This records observed results and unresolved work; repository code and any newer user-provided logs take precedence.

Latest checkpoint: the recording-driven annotation layout/removal fix is implemented in editor-rfdetr-v4.html. It embeds the same annotations-user-confirmed-v3.json. The recording shows newer unseen browser edits: the user must download JSON from v3 and import it into v4 before continuing. See the final section, docs/ANNOTATION_UI_FIX.md and docs/RFDETR_ANNOTATION.md. RF-DETR is not integrated into the native app, fine-tuned or adopted. Earlier sections are historical; do not repeat completed cluster setup/acquisition, model installation/download or RF inference without new evidence.

## Project and working constraints

- The user's normal checkout is `C:\Users\nazee\Documents\All Modules\FrameTrail`. Work on FrameTrail, not the unrelated MiniERP project that hosted the previous chat.
- An auxiliary checkout used by the previous chat is `C:\Users\nazee\Documents\All Modules\MiniERP\MiniERP-Springboot\FrameTrail`. Do not copy/reset either checkout blindly. Inspect Git status and preserve local changes before synchronizing anything.
- Repository: `https://github.com/MogProgJ/FrameTrail`, private, branch `main`. Training handoff scripts were committed as `94b986d`; dataset/training tooling as `c6c4e6e`.
- Preserve the user's untracked `gemini_generated_video_07b260f6-analysis.csv` and other footage/results.
- The approved saved-analysis choose/drop → analyse → review appearances/timestamps → optional save/CSV workflow must stay as accepted.
- Work in bounded modules, verify relevant changes, keep the GUI minimal, and do not promise flawless execution or unlimited recognition.
- The user is new to cluster commands. Explain whether each command runs in Windows PowerShell or the Linux cluster terminal, and give concrete commands in manageable steps.
- No passwords, OTPs or keys belong in prompts, repository files or logs shared with the assistant. Account names are not recorded in this repository handoff; the user already has their working SSH command.

## Product and training scope

The app is a native C++/Qt/FFmpeg video-analysis application with ONNX Runtime CPU/DirectML detection, resumable playback, live webcam intake, tracking/line counts and saved object appearances/CSV exports. Desktop application version remains 0.12; 0.13 describes offline dataset/training tooling.

The actual goal is broad everyday-object recognition. Fox/dog, low light, small objects and occlusion are difficult evaluation slices, not a wildlife-only project. RF-DETR Small has now been installed and tested in isolated offline CPU tooling, but has not been trained by FrameTrail or integrated into the native app. Existing full-vocabulary YOLO Open Images is the first mechanically compatible training baseline. YOLOX-S remains the app's default when installed; no training candidate has been adopted.

Current Open Images contract: 601 raw model outputs, mapped to 597 canonical app categories. Arbitrary smaller heads and RF-DETR need an explicit native adapter/vocabulary contract. Retaining outputs does not prove retained accuracy.

## Dataset and local training: already completed

- Official publisher validation metadata was indexed: 41,620 image records, 303,980 boxes, 570 raw labels with boxes. This is a catalogue, not 41,620 downloaded photographs.
- Downloaded sample: 96 real images, 447 annotated boxes, 132 canonical categories, six broad domains. Source-group partitions: 70 train / 11 validation / 15 test.
- Images remain clean; annotations are separate YOLO text and COCO JSON files. Complete immutable bundle: `output/training-0.13/general-smoke-bundle/`.
- The sample has incomplete, unreviewed annotations and comes from publisher validation data. It is explicitly mechanical-smoke-only. Production-mode preflight rejects it. Do not turn review flags on without review or use it to claim general accuracy.
- A real one-epoch CPU training check completed locally, followed by full-vocabulary ONNX export and native CPU/DirectML numerical/vocabulary checks. All 29 Python checks passed at the tooling stage. These checks establish limited mechanics/integration, not an accuracy improvement.
- Useful local artifacts: `output/training-0.13/general-smoke-run-final/`, `general-smoke-final.onnx`, and `general-smoke-final.export.json`. Original app models are untouched.

## KIT cluster: latest observed state

Host: `uc3.scc.kit.edu`. Authentication is interactive password plus OTP in the user's terminal. The assistant has not logged in or operated the remote account; remote outcomes below are from the user's terminal output.

1. GPU diagnostic job **7441565** completed with exit code 0 on **NVIDIA A100 80 GB**. Reported driver: 595.71.05; driver CUDA support: 13.2. The documented queue `dev_gpu_a100_il` accepted the job.
2. Workspace **frametrail** was created for 30 days. Resolve its actual location using `ws_find frametrail`; the training folder is `$(ws_find frametrail)/FrameTrail`. Workspaces expire and have no backup; preserve results locally.
3. Available/working module: `devel/miniforge/25.3.1-python-3.12`; loaded Python is **3.12.11**.
4. The prepared archive `frametrail-cluster-smoke.tar.gz` and its `.sha256` were uploaded to cluster home. The cluster reported **SHA256 OK**, and extraction into the workspace completed without reported errors. Archive is about 77 MB (74 MiB), contains 311 files and a provenance manifest; it excludes Windows label caches, Python environments and unrelated user files. Original upload package remains under local `output/training-0.13/`.
5. The first environment installation was interrupted with Ctrl+C. Training attempt **7442046** subsequently failed with `ModuleNotFoundError: No module named 'torch'` before training. No experiment folder/checkpoints were created for that attempt. Treat this job as failed historical evidence, never as the latest successful run.
6. The user reran `bash -l training/setup-cluster-env.sh` successfully. Terminal output ended with **No broken requirements found** and **Environment installed**.
7. User then confirmed imports from the project's `.venv`: **PyTorch 2.8.0+cu128**, **Ultralytics 8.3.228**. The one-off import warned about the home settings directory and used `/tmp/Ultralytics`; our training runner sets `YOLO_CONFIG_DIR` inside the project before importing Ultralytics.
8. Replacement training job **7446193 completed with Slurm exit code 0**. The user's log confirms actual CUDA training on the A100 and experiment status `completed`: one epoch, image size 320, batch 2, 70 train / 11 validation images. The training wrapper took 106.91 seconds; the complete Slurm job took 3 minutes 44 seconds. Both checkpoints were saved. The 15-image locked test remains untouched, and `approved_for_application` remains false.
9. The user downloaded the complete experiment and Slurm log to the usual checkout's `output/kit-results/7446193/`. Local verification matched both checkpoint hashes against the experiment report and the previously supplied identities; the environment snapshot hash also matched. Checkpoint SHA256 identities: `best.pt` = `77723b84f509ed4dba7d78bac60fb4de00250f3b2bd0d5e6e158bc34c68ac37b`; `last.pt` = `f7f80e66e6bb143bc882baae1c2ff5c6348281151163e6016693a2f417a007e6`. Dataset lock SHA256: `9c71e1b1d749f1d2c97604fc37aa363c51831e3838e5c7254bd26ba1016cb0b2`. `code_revision: null` is expected for the minimal upload without Git; the transfer manifest and experiment source hashes provide provenance.

## Immediate next step

Retrieval and local checkpoint/environment identity checks are complete. The experiment is at `C:\Users\nazee\Documents\All Modules\FrameTrail\output\kit-results\7446193\cluster-smoke-7446193`; the adjacent Slurm log confirms completion. Do not repeat workspace creation, upload, installation, retrieval or the smoke job unless new evidence warrants it. Proceed to a bounded larger-dataset acquisition/review plan and independent broad-domain evaluation. Optional export/native checks of this GPU checkpoint can verify compatibility, but cannot establish accuracy improvement.

In the cluster terminal:

```bash
cd "$(ws_find frametrail)/FrameTrail"
sha256sum output/cluster-smoke-7446193/weights/best.pt output/cluster-smoke-7446193/weights/last.pt
```

Compare these hashes with the recorded checkpoint identities above. To review the completed job:

```bash
tail -n 80 frametrail-smoke-7446193.log
cat output/cluster-smoke-7446193/experiment.json
```

The commands above are optional remote rechecks; the downloaded artifacts have already passed local identity checks. The supplied log establishes cluster training mechanics, not general recognition accuracy; partial validation metrics from this tiny unreviewed sample must not be presented as product accuracy.

The smoke script requests one GPU for at most 15 minutes and uses partition CPU/memory defaults. It loads the working module, tests CUDA on the allocated node, validates the exact dataset/checkpoint, and trains one epoch using the existing sample. The test partition stays untouched. Heavy training must run through Slurm on compute nodes, not directly on a login node.

The GPU smoke succeeded. Do not replace the app detector with its artifact. The next substantive work is a bounded acquisition/review plan for larger broad-domain data and independent evaluation before a substantial training run.

## Work after cluster mechanics are proven

Prepare larger, balanced source-train data, an explicit approach to incomplete annotations, and independent real-footage evaluation across broad domains. Open Images is the current compatible base; LVIS is a later broader-vocabulary candidate, Objects365 has academic-only terms, and COCO alone offers only 80 categories. Public dataset size does not establish suitability or accuracy. Existing broad weights are already Open Images-pretrained, so another large run is not automatically an improvement.

A proposed first substantial dataset budget was 25,000–50,000 images, with scaling toward 100,000+ conditional on measured benefit. This larger set has **not** been acquired/prepared. Do not start a substantial training job with the current smoke bundle or launch a large download without a concrete bounded acquisition plan within the user's scope. RF-DETR adapter/training/evaluation is subsequent work, not completed work.

## Read these files as needed

- [KIT command guide](docs/KIT_CLUSTER_QUICKSTART.md): transfer, setup, submit and result commands.
- [Training guide](docs/TRAINING.md): dataset limitations, tools, evidence and next gates.
- [Training readiness](docs/TRAINING_READINESS.md), [roadmap](docs/ROADMAP.md), [status](docs/STATUS.md): broader plan/history; older "no cluster job" statements predate the user-reported results above.
- [Local evidence](docs/benchmarks/training-0.13.json): immutable stage evidence, not a claim of completed cluster training.
- [GPU smoke job](training/run-cluster-smoke.sbatch), [environment setup](training/setup-cluster-env.sh), [smoke configuration](training/general-cluster-smoke.json).
- [Training runner](scripts/train-detector.py), [dataset contracts](scripts/training_data.py), [export](scripts/export-trained.py), [requirements](scripts/requirements-training.txt), [dataset tests](tests/test_training_data.py).

Keep photographs, training weights, archives, environment directories, private raw logs and footage outside tracked source files. The historical local evidence JSON predates this successful cluster run; use the latest user-provided report and this handoff for current cluster state.

## Larger-dataset preparation continuation (4 October 2026)

The user approved starting larger-dataset preparation. The acquisition plan is
docs/DATASET_ACQUISITION.md, with a bounded 600-image intake policy and verified
Open Images publisher-train metadata sources under training/. No new train
photographs, reviewed bundle or substantial training job have been acquired.

User-supplied storage output: the existing workspace has roughly 29.5 days left
and lists expiry on 3 November 2026, with three extensions available. /pfs/work9
quota shows 8.569 GiB used against 40 TiB soft / 44 TiB hard limits; output is
99 MiB and .venv 7.3 GiB. curl is available and cpu_il was listed with idle nodes.
The filesystem's 1.5 PiB free is shared capacity, not the user's allowance.

scripts/acquire-cluster-metadata.py and training/run-cluster-metadata.sbatch
prepare five source/reference files, the train SQLite catalogue and all-class
inventory using the existing environment. They request one CPU, 8 GiB RAM and
two hours on cpu_il; no GPU, photographs or training. Raw human image-level
labels are downloaded but are not yet indexed or integrated into the loss.
Six focused local tests passed for acquisition budgets, resumable interruptions,
changed-object rejection and completed-file integrity. The user subsequently
submitted metadata job **7447265**, which completed with Slurm exit code 0 in
5 minutes 18 seconds. Its preparation report status is completed. All five
metadata/reference files were acquired and hashed; the train catalogue has
1,743,042 image records, 14,610,229 boxes, 601 raw labels / 597 canonical
categories, and 599 raw labels with boxes. Catalogue SHA256:
bd42dbb1129406c16cda37401670ecba04d6d956cde0071ab79de6190162e78d.
These results are from the user's supplied cluster log/report; the full catalogue
has not been retrieved locally. No photographs have been downloaded.

The prepared small transfer package is
output/training-general-v1/frametrail-metadata-tools-v1.tar.gz with a SHA256 file.
It extracts into output/training-general-v1/metadata-tools-v1. Only this new
tools package needs transfer; do not repeat the original training upload/setup.
Follow the transfer/submission commands in docs/DATASET_ACQUISITION.md and use
the new job's actual ID. Reports go to
output/training-general-v1/catalogue-JOBID/preparation.json and inventory.json;
metadata/receipts are shared under output/training-general-v1/source-metadata.
Do not submit concurrent metadata jobs. After verified completion, inspect
coverage and persist the pilot selection before any bounded photograph download.

Next stage: training/run-cluster-selection.sbatch uses the completed catalogue
and already uploaded pilot policy, verifies the catalogue/policy hashes, reports
zero-box labels, excludes old smoke image IDs, and persists up to 600 candidate
IDs plus a selection summary. It requests one CPU, 4 GiB RAM and 30 minutes on
cpu_il, with no photograph download or training. Transfer just this new script
to cluster home as frametrail-selection-v1.sbatch, then submit from the project
with --export=ALL,FT_CATALOGUE_JOB=7447265. This historical v1 step subsequently
completed as job 7448416 (see latest continuation below). Its log is frametrail-selection-JOBID.log and output is
output/training-general-v1/pilot-selection-JOBID/. Inspect selection-summary.json
and source inventory before implementing acquisition of these persisted IDs.

### Selection 7448416 verified; balanced revision prepared

The supplied submission/accounting/log agree on selection job **7448416**,
COMPLETED with exit code 0 in 46 seconds, using catalogue **7447265**. The earlier
missing frametrail-metadata-7448416.log was a wrong log prefix, not a job failure.
The actual log is frametrail-selection-7448416.log.

The user retrieved the three JSON outputs to
output/kit-results/7448416/pilot-selection-7448416/. Local checks matched the
selection SHA256 f09990778704c7e51d54295fa88e0b39da0a840f77cc7fa6de01a06e16869d15,
policy, publisher train, summary domain counts, 601 raw IDs / 597 canonical
categories and inventory counts. All 600 selected IDs are unique and none
overlap the old 96-image smoke manifest. All six domains are represented.
Container and Kitchenware have no direct raw box labels in the source catalogue.

The selection covers only 50 of the policy's 52 acquisition anchors (12 IDs each).
Lantern and balloon are absent because the v1 sampler reaches its 600-ID cap
before querying those last anchors. Their eligible supply has NOT been checked;
this is not evidence of a publisher shortage. 52 times 12 requires 624 slots.

scripts/select-balanced-pilot.py and training/run-cluster-selection-v2.sbatch
implement a separate anchor-round-robin-v2 revision: one ID per anchor per round,
all-anchor eligible counts, unchanged filters/seed/scope, deterministic selection,
old smoke ID exclusion, source/policy/vocabulary/prior-selection hash checks and
exclusive job-specific output. It never edits the old selection or catalogue and
never downloads photos. A successful coverage gate requires 600 unique IDs and
at least one acquisition anchor in every requested category/domain. Missing
anchors or inadequate total supply produce coverage_failed and a nonzero exit.
With ample non-overlapping supply, anchors receive 11 or 12 IDs within the cap;
these are selection intent, not exhaustive object-label counts or review approval.

Seven SQLite-only selector tests and six metadata acquisition tests passed locally.
The new 4,164-byte package is
output/training-general-v1/frametrail-selection-tools-v2.tar.gz with adjacent
SHA256 file. It contains only the new selector and new CPU job, both LF-ended;
archive SHA256 4ac01576ca4ef239b1a222c837fd8a9b99782311d95dc106bb0f8de431f3024b.
Do not repeat the environment, metadata or original training uploads. Transfer
this package, verify, extract with --keep-old-files, check Bash syntax on KIT,
and submit using FT_CATALOGUE_JOB=7447265,FT_PRIOR_SELECTION_JOB=7448416.
This historical note predates verified v2 job 7449188 (see latest continuation below). Use its actual returned ID for
frametrail-selection-v2-JOBID.log and pilot-selection-v2-JOBID/.

Next gate: verify v2 Slurm exit 0, completed summary, coverage_gate_passed true,
600 unique selected IDs, all 52 anchors, eligible counts and selection hash.
Then implement bounded/restartable acquisition FROM those persisted IDs, retaining
per-image receipts, decode validation and incomplete review flags; review a first
60-image batch before scaling. No train photographs or larger reviewed dataset
have been acquired. Image-level supervision, independent real-footage evaluation,
rights/label-completeness review and substantial training remain unresolved.

### Latest: balanced selection complete; first-60 photo module prepared

Selection job **7449188** completed with exit 0 in 45 seconds. Downloaded files
and log are at output/kit-results/7449188/. Local checks matched seven input/
artifact hashes, exact log/summary agreement, 600 unique publisher-train IDs,
all 52 anchors/six domains and zero overlap with the old 96 smoke IDs. Selection
SHA256: 69d67561b87f4efad265f4713a415ff985e7bc551fa01b931c574c1e16d68ef5.
28 anchors receive 12 IDs and 24 receive 11; lantern/balloon each receive 11.
The job reports 462/1,344 eligible lantern/balloon IDs respectively. The full
remote catalogue has not been independently rehashed/queried locally.

scripts/acquire-pilot-images.py and training/run-cluster-photo-pilot.sbatch now
implement the bounded first-60 prefix of that exact selection. It covers all
52 anchors, with domain intent counts 10/10/10/9/9/12 in policy domain order.
The module retains clean original JPEGs, publisher boxes/attribution, per-image
receipts, safe HTTP-range checkpoints, decode checks and duplicate holds against
the intake/old smoke set. Completed identities and human notes are preserved;
edited manifests fail closed. Review flags remain false and partitions unassigned.
No app/model change, training, synthetic image generation or approval occurs.

The small package is output/training-general-v1/frametrail-photo-tools-v1.tar.gz
with adjacent SHA256 file. Transfer only this new package. It extracts into
photo-tools-v1; existing catalogue, selection, .venv and training uploads are
reused. Follow docs/PHOTO_ACQUISITION.md for manual transfer/submission/status/
retrieval/review commands. The CPU job requests one CPU, 4 GiB and two hours on
cpu_il with FT_SELECTION_JOB=7449188. First-60 original payload is bounded by
1 GB total/10 MB per image (at most 600 MB for 60), plus small metadata. Network
retransmissions are not part of the stored-payload cap.

At preparation time no photo job had run; this was subsequently completed as
7450934 (see latest evidence below). Use its actual Slurm ID for frametrail-photos-JOBID.log
and output/training-general-v1/photo-job-JOBID/acquisition.json. The resumable
intake directory is output/training-general-v1/photo-pilot-7449188-first60/.
Require Slurm COMPLETED/0:0, acquisition completed, 60 decoded photos, no failed
IDs, intact receipts/manifest and all 52 anchors before declaring acquisition
successful. Duplicate holds/rights/label completeness remain separate review work.

The downloaded review.html is an offline inspection aid, not an annotation
editor or the approved saved-analysis application. Record findings in a separate
copy of review-notes-template.md; do not enable manifest booleans or treat the
unassigned intake as a training/export bundle. Whole-image corrections, hierarchy/
unknown flags, rights evidence, reviewed splits, independent real footage,
cross-source leakage checks and partial supervision remain unresolved. Inspect
these 60 before acquiring the remaining 540 or any substantial dataset.

Local photo-module verification: 16 tests passed for HTTP limits/range identity,
interruption/publication recovery, corruption protection, decode, OS locks,
fake first-60 intake, visible failed IDs, provenance checks and preserved notes/
edited manifests. Seven selector and six metadata tests also passed. Archive
size: 10,478 bytes; SHA256:
51a858c774aeeb34d3d9460695012b0264b83a9fb08de419ccb9cecaf89c9323.
Python syntax, source/package identity and LF line endings were checked locally.
Linux Bash syntax/actual CVDF network success still require the manual KIT run.

### Latest verified acquisition: photo job 7450934

The user's submission, Slurm accounting, report and downloaded log agree on
photo job **7450934**, COMPLETED/exit 0 in **1 minute 7 seconds**, on cpu_il.
Source selection is **7449188**, source catalogue **7447265**. The initial missing
log while PENDING was normal: it existed after the job started.

The user retrieved the first-60 intake, log and acquisition.json to
output/kit-results/7450934/. Local independent checks verified all **60 JPEGs**,
all **60 receipts**, image sizes/hashes, decoded dimensions/dhash/luma, exact
first-60 selection membership, source/policy/vocabulary/exclusion/runner hashes,
manifest/progress/report agreement and preserved 601-raw/597-canonical mapping.
Original bytes: **17,984,698** (about 17.98 MB). Publisher boxes: **322**, across
89 raw labels; these are unreviewed box counts, not completeness or accuracy.
All 52 anchors/six domains are present; domain counts are 10/10/10/9/9/12.
No failed downloads, partial image files, old smoke ID overlap or exact/simple
dhash duplicate candidates were found. This limited duplicate screen is not
proof against crops/video neighbours or deployment leakage.

Manifest SHA256:
a7f1cd4e65482eeae54b691dc24f8d18f6b52cb06e3ca5045ed0801aee0aeea0.
The user opened the offline review page, and their screenshot shows clean
photographs with publisher-box overlays. The first image's larger canonical
person boxes and smaller human-face boxes are different categories, not new
model predictions. Opening/viewing the page does not complete annotation review.

Acquisition mechanics and local retrieval verification are complete. Do not
repeat setup/upload/selection/download without new evidence. The next task is
whole-image annotation/rights review and a correction workflow: start with the
first six (one per domain), record missing/wrong objects/boxes and uncertainty,
then review the full 60 before deciding expansion. The remaining **540** pilot
candidates are still IDs, not acquired photographs. Review flags remain false,
partitions unassigned, approved_for_training false; no training/export/model
adoption or accuracy improvement follows from this intake. Preserve local notes,
the old 96-image smoke dataset and the approved saved-analysis interface.

## Accepted visual audits and annotation drafts (4 October 2026)

The user accepted all 60 visual audits and authorized converting findings into
annotations. This acceptance does not approve box completeness, source-use rights,
partitions, training or model adoption. Original manifest, photographs, receipts,
review.html, my-review-notes.md and assistant-audit-15-60.md remain unchanged.

New local module: scripts/annotate-pilot.py, annotation_review.py,
annotation-editor.html, annotation-proof.py, training/annotation-policy-v1.json,
and tests/test_annotation_review.py plus test_annotation_editor.cjs.
See docs/ANNOTATION_REVIEW.md for commands, policy and progress. No app/native
source or model was changed; no substantial training/download job was submitted.

Workspace: output/kit-results/7450934/photo-pilot-7449188-first60/annotation-workspace-v1/.
Latest state: annotations-corrected-v2.json; editor: editor-corrected-v2.html;
annotation-only export: draft-export-v2/. Preserve earlier snapshots/proofs.
The assistant ran the existing native Open Images model locally on all 60 images
for suggestions, retaining its identity and CSVs. This is the existing broad
pretrained model, not the smoke checkpoint or an independent quality test.

There are 322 publisher records, 84 model proposals and 137 manual proposals.
After 209 logged correction events: 35 individual assistant confirmations, 489
pending boxes and 19 rejected records (524 active draft targets). All 60 images
retain unresolved holds; no whole-image geometry/coverage pass is recorded.
Manual geometry is estimated and still needs precision QC. Drafts retain 601 raw
labels / 597 canonical categories; exports are unassigned/unapproved and produce
no data.yaml or dataset lock. Do not pass the drafts to training or claim accuracy.

Next: precise boundary/class QC and whole-image coverage, release-level hierarchy,
parts/flags/extent policy and intended-use rights review, then stronger duplicate/
group-split checks and a small reviewed release plus independent real-footage
evaluation. The remaining 540 pilot images are still not acquired. Do not repeat
uploads, setup, selection or acquisition. Keep the approved saved-analysis flow.

All 75 Python tooling tests passed, including the new annotation/export checks;
full-editor JavaScript syntax and pure replay/import tests passed. The final
draft export verifier checked 60 exact photograph references, 60 YOLO files and
524 active COCO/YOLO targets; training preflight rejected unassigned partitions.
The report is draft-export-v2/verification-exact-references.json. The
built-in browser blocked local-file preview; actual browser drawing/resizing/
download/resume interactions remain unverified. Do not work around that browser
policy; the user can open the offline editor in their normal browser.

## Annotation editor usability fix (4 October 2026)

The user's screenshots demonstrate a successfully drawn bracelet rectangle that
inherited Clothing and the previous garment note. The old datalist was not a
usable dropdown for them. Bracelet is absent from the frozen model vocabulary;
do not map it to Clothing/Necklace or add a 602nd training class as a UI fix.

New page: `annotation-workspace-v1/editor-simple-v3.html`, using the unchanged
`annotations-corrected-v2.json` base. Existing pages/snapshots/photos/notes/exports
are preserved. Browser-session changes (including the user's extra rectangle)
have NOT been retrieved into the filesystem. Save JSON in the old page before
switching, then import that file into v3. The new page supports earlier JSON and
can convert the wrongly labelled rectangle without redrawing it.
The new editor writes a version-specific autosave key and only reads the legacy
key as a fallback if the browser exposes it; old-page autosave is not overwritten.

Source: `scripts/annotation-editor-simple.html` and `annotation-editor.js`, embedded
into the self-contained generated HTML (no external scripts/network). A real
search-filtered select replaces the datalist; Add a box now draws before asking
for a label, with no inherited label/note. Coordinates, removal/source/history
and whole-image/rights checks are expandable; errors are visible beside controls
and in a fixed status bar. Unsaved box fields block navigation/import/download
instead of being silently lost. Backup/download remains an explicit user step.

Outside-model rectangles are append-only `observation-add`/`observation-update`
events, stored separately in per-image `observations` (no raw class ID). Supported
box↔observation conversion rejects/preserves the old record and adds a new one
atomically in JavaScript. Python validates the same history. Observations stay
in annotation JSON and a new export sidecar but are excluded from COCO/YOLO
training targets. They are NOT ignore masks, training readiness or a new model
capability. The frozen 601/597 mapping and all training/rights gates are unchanged.

All 81 Python tests passed, including cross-language conversion/export tests;
JavaScript syntax/replay/import/picker/draft/form-stub tests passed against the
existing 60-image state. The generated v3 page's exact embedded payload/script
and syntax were checked. Actual browser interaction/rendering remains unverified
because local-file preview is blocked; no browser workaround was used. The user
should check the dropdown, bracelet conversion and save/import in their browser.
No new acquisition/training job, model adoption or native saved-analysis UI change.

## RF-DETR Small isolated probe (7 October 2026)

The user agreed to an isolated pretrained Small evaluation/export module, keeping
the app native C++, with no GUI redesign/default replacement/substantial training.
New scripts: setup-rfdetr-probe.ps1, requirements-rfdetr-probe.txt, rfdetr_probe.py,
probe-rfdetr.py and review-rfdetr-probe.py. See docs/RFDETR_PROBE.md for exact
Windows commands, contracts, limitations and next gates. No MiniERP changes,
cluster access/submission, additional dataset acquisition or camera activation.

Environment .deps/rfdetr-probe-cpu uses Python 3.12.14, torch 2.8.0+cpu,
torchvision 0.23.0+cpu, rfdetr 1.11.2, onnx 1.19.1, onnxruntime 1.30.0,
numpy 2.2.6 and pillow 12.3.0. pip check passed. Setup reuse verifies package/wheel
identity and preserves the existing install receipt instead of overwriting it.
Full resolved packages/install receipt are saved locally and in the completed run.

Official Small checkpoint acquired once into .deps/rfdetr-probe-assets; exact
386,045,550-byte object under an explicit 400 MiB cap. Publisher MD5 matched;
local SHA256 d81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33.
Publisher commit 7433d5919d0f7e72cc6cb78663e0a731afd499e0; wheel SHA256 matched
2f23589567123b59302f1cfa9d14d23630f9f583ee6f3468c5891e33fb103b2a.
Do not repeat acquisition or install an unpinned develop release without cause.

Completed result: output/rfdetr-probe/cpu-v3/experiment.json and comparison.html.
Six existing first-60 publisher-train photos were used only as mechanics inputs.
SDK inference, explicit sparse COCO decoder, ONNX export/checker and ONNX Runtime
CPU inference ran. Native YOLOX-S/Open Images CPU outputs are saved separately.
The static float32 ONNX is 114,434,018 bytes; SHA256
a7d8e54b0e8aebc67c0de798f0e8951f9566d82e0ffa0a9cd4b4a22a3138d46d.

All 42 returned RF predictions above 0.35 match bidirectionally by class/box/score;
24 above 0.55 produce 48 directional strong matches. Worst IoU 0.9996729,
score delta 0.0003576 (limits 0.98/0.003). These are numerical agreement, not
correct-object counts or product accuracy. Raw positionwise query tolerance is
false: low-confidence arrays differ, and query positions are not object identities; no raw tensor
equivalence on these or other inputs is claimed. See per-image raw deltas.
cpu-v1's blank-native-fallback parsing failure and cpu-v2's raw-array tolerance
failure are preserved; v3 records the decoded-output rule explicitly.

RF-DETR's frozen probe input is RGB [1,3,512,512], ImageNet normalization, direct
bilinear tensor resize/antialias=False; named outputs dets [1,300,4] and labels
[1,300,91]. Official sparse COCO slots map to the existing 80 canonical classes;
slot 90 is toothbrush, not background. This is not a 597-class broad model and
cannot be passed to an existing single-output native profile. RF native adapter,
schema-compatible profile registration, DirectML/video/resource checks and held-
out accuracy evaluation remain undone. training_performed/accuracy_evaluated/
approved_for_application are false. The CPU probe does not prove GPU operation.

Original photos/manifest, notes, accepted audits, annotation state, app models and
saved-analysis UI are preserved. The preview is read-only model guesses, not the
annotation editor; static content/tests were checked, browser rendering was not.
Next: obtain the user's corrected annotation JSON, validate geometry/coverage/
rights/policy and freeze independent everyday-object evaluation. Compare the
pretrained candidates fairly before deciding native RF integration or KIT fine-
tuning. Remaining 540 candidates are still not acquired; no larger approved
training bundle exists. Corrections do not automatically learn an annotator.

Verification: all 100 Python tooling tests passed (19 RF probe/comparison tests).
Existing annotation-editor syntax/pure replay/import/picker tests and exact v3
embedded payload checks passed. PowerShell setup syntax/reuse and pip consistency
checks passed. Original manifest, both audit-note files, review.html and annotation
v2 hashes match their recorded identities. Both native baseline model hashes and
the exported RF model hash matched after the probe. No native C++ code changed;
no native rebuild, RF DirectML test or browser-rendering verification is claimed.

## RF-DETR-assisted annotation module (7 October 2026)

The user explicitly authorized generating RF-DETR annotations and reviewing them
in the existing offline box editor, not native app integration or training.
New scripts rfdetr_annotations.py/annotate-rfdetr.py reuse the verified cpu-v3
ONNX in the existing pinned environment. All 60 current photographs were processed;
318 unreviewed proposals were recorded (277 exact-vocabulary mapped; 41 observation
only). No new data/model download, setup repeat, Slurm job or camera activation.

New sibling workspace:
output/kit-results/7450934/photo-pilot-7449188-first60/annotation-workspace-rfdetr-v1/.
Latest page editor-rfdetr-v2.html; initial editor-rfdetr.html is preserved.
See docs/RFDETR_ANNOTATION.md for simple review steps and exact Windows commands.
The source seed is byte-identical to the old seed; initial annotations.json equals
the old prepared v2 state, retaining all 209 corrections and 543 records. Earlier
pages/states/notes remain unchanged. Unseen browser edits have not been received:
save JSON in the old page, then import it here. RF autosave uses a separate key.

Proposals stay in a separate immutable catalogue until human Save/Confirm/Remove.
Teal dashed overlays and a clickable queue preselect the suggested class and
geometry. Draft corners resize before saving. Overlap warnings require explicit
duplicate handling; the user can apply RF geometry/class to a matching saved box
without adding an active duplicate, preserving both old history and original RF
prediction. This explicit action marks the target pending and resets existing
whole-image passes for rechecking. Rejection needs a reason. No automatic replacement
or approval occurs. Older seed-compatible JSON can be imported; RF-decision JSON
requires this RF workspace/catalogue for Python validation and export.

The frozen 601/597 vocabulary is unchanged. Twelve COCO categories have no exact
registry mapping (cow/frisbee/skis/sports ball/cup/donut/potted plant/dining table/
remote/keyboard/microwave/hair drier); do not guess similar class IDs. Their 41
proposals default to provenance-linked observations, excluded from training
targets unless the human explicitly chooses a defensible supported label.
Bracelet and other custom names remain observations, not trained classes.

Completed preparation.json and rf-proposals.json are retained. Catalogue SHA256
84fd28d3c33d85d6af19d487416048c944b37a8d8410ad9ab564326b887c7281;
latest editor SHA256 282e7f3c18dca377951ccf6396d20e16db87926fc6c998884a722c76da199c74.
All 111 Python tests passed, including 11 new RF annotation checks and JS→Python
history replay. Pure JS/form/payload tests passed on the real workspace. All 318
prediction representations and all 60 original-photo identities were checked;
base state/seed, notes and ONNX identity remain unchanged. Real browser dragging,
dropdown rendering and download/re-import are not verified: the user should try
one photo first. No local-file browser-policy workaround or MiniERP edit occurred.

Next: user review and saved JSON retrieval; validate full-image labels/policy/
rights, then reviewed splits/leakage and independent everyday-object evaluation.
No larger approved bundle, RF fine-tuning, native adapter/DirectML integration or
accuracy improvement exists. Remaining 540 pilot candidates are still unacquired.

## Saved JSON audit and authorized editor repair (8 October 2026)

Input: user-supplied frametrail-annotations-2026-10-08T17-30-05.755Z.json from
Downloads; SHA256 24076c82ba6dfa4b611d108ce8326e907fc2b4a2ef10ca8b6549baadc8067b7c.
It passed full source/photo/seed/catalogue/history checks: 318 events, with the
209-event baseline prefix unchanged and 109 new local-reviewer actions on 26
photos. No new confirmation events were recorded. Two legacy linked RF records
had been reopened as pending, duplicating a car in photo 38 and the whole apple
in photo 39. The three publisher apple boxes were pending, not confirmed.

The user then explicitly authorized fixing the editor, treating saved individual
boxes as confirmed, and making RF-to-existing-box updates confirm directly.
Source changes affect only offline annotation tools, not the native app/MiniERP.
New append-only proposal-link events carry an immutable linked_to target ID.
Validators require a checked RF source, active same-photo matching category,
unchanged source geometry/class/provenance, and a rejected duplicate record.
Generic updates cannot reactivate or rewrite a linked duplicate. RF list status
resolves to the real saved target, and selecting its RF row selects that target.
Legacy links are recognized from their full same-transaction history, not a note
alone. Saving a box confirms directly; advanced Mark pending/restore/resize are
explicit recheck paths. Downloading JSON does not bulk-confirm untouched records.

scripts/repair-annotation-saves.py requires --confirm-user-saved and a NEW output.
It reconstructs the five historical links, rejects the two reopened duplicates,
and confirms only current pending records touched by the user's new saved events.
No geometry/labels/source provenance/review/rights/approval flags are changed.
Original upload and all 318 existing events remain intact. The derived snapshot
annotations-user-confirmed-v3.json and adjacent repair receipt are in the RF
workspace; 78 repair events were appended (five links, 73 confirmations: 42
supported records and 31 observations). Counts: 74 confirmed / 473 pending / 27
rejected supported records, plus 31 confirmed observation-only records. All five
linked targets and all three apple boxes are confirmed. No exact active same-
canonical-category duplicate boxes remain. Untouched drafts remain pending.

Latest page: annotation-workspace-rfdetr-v1/editor-rfdetr-v3.html. It embeds the
repaired user state; no old-JSON import is needed. Preserve any newer unseen old-
page edits separately before switching. The new autosave key leaves older keys
untouched. Import refuses old snapshots with active legacy duplicate links; older
editors cannot replay the new link events. Earlier pages and snapshots are kept.
Repaired JSON SHA256 5a48d622104c367ee9806d70cef8621f9fb6955dfaefcd8e444f266e8740831f;
latest editor SHA256 46ef0e0d7a3a9fcda16c8a5d440f748e29403248c698c270c24c0e78f6ffb641.

All 117 Python tests and pure JS/payload/form/link checks passed, including the
real resumed-state payload and migration preservation checks. All 60 original
photos and the uploaded JSON were rechecked. Browser interaction remains unverified;
the user should try one save and JSON backup. No browser-policy workaround, new
model/data acquisition, RF inference rerun, training job or native adoption occurred.
Individual confirmations follow explicit user approval, not independent visual
accuracy verification. All 60 images still have holds and no whole-image geometry/
coverage passes; observations stay excluded from training classes. Continue user
review, validate the next saved JSON, then policy/rights/split/evaluation gates.

## 8 October — recording-driven editor layout/removal fix

User recording 20261008-2039-40.8233351.mp4 was inspected through two extracted
frames. It shows the removal error while the separate Box note accordion is
collapsed, and a long scrolling sidebar whose sticky editor outlasts the photo.
The scoped Product Design audit informed the fix; see docs/ANNOTATION_UI_FIX.md.

V4 uses a desktop viewport shell, an uncropped aspect-ratio fitted photo with SVG
aligned to its exact rendered rectangle, a non-sticky bounded editor and separate
Saved boxes/RF suggestions tabs. Only overflowing panel contents scroll. Narrow
windows stack normally. Review/help are closable dialogs. Removal has a dedicated
visible reason input beside its action, focuses it on empty input, preserves
original records/history, and refuses to discard unrelated unsaved edits. Typed
removal reasons block navigation/confirmation until resolved. Save=confirm and
RF linked-duplicate exclusion remain unchanged.

Generated NEW editor-rfdetr-v4.html, SHA256
5716d119338ba8053d692ce9a81a2e194fd5f918db7d33802c886ffdb81c2473.
V3 page, original Downloads JSON, repaired snapshot and RF pack hashes matched
their prior identities. Generation checked the immutable intake/60 photograph
hashes and embeds exactly the same repaired state and pack. No annotation events
were added; draft/training approval remain unchanged. Newer edits visible in the
recording have NOT been supplied as JSON. Before switching, download the current
v3 JSON and import it into v4. V3-compatible autosave is retained as a convenience,
not a substitute for this backup/import step.

All 120 Python tests passed. Pure JS tests on base and RF editor state/payload
passed, including missing/valid removal reasons, RF rejection provenance,
unsaved-edit guards, image-fit/coordinate mapping and tab visibility. Live local-
file browser access is policy-blocked; no workaround was used and no new rendered
UI, real dragging, dialog behavior or browser save/import is claimed tested.
Ask the user to try one removal and JSON export/import before a long session.
No MiniERP/native saved-analysis changes, training, inference rerun or acquisition.
