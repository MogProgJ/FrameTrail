# Larger general-recognition dataset: acquisition and review

Prepared 4 October 2026. Status: train metadata/catalogue job 7447265 and balanced
pilot selection job 7449188 completed and were verified. First-60 photo tools
are prepared; see [the photo acquisition walkthrough](PHOTO_ACQUISITION.md). No train photographs,
reviewed bundle or substantial training run acquired by this stage. Cluster
training mechanics and retrieval were proved by job 7446193.

## Decision and first deliverable

Build a versioned subset from the Open Images publisher **train** split, then
add permissioned real photographs/video frames that represent FrameTrail use.
Keep the full existing 601 raw labels / 597 canonical categories. The first
deliverable is a coverage inventory and a review pilot of **up to 600 images**,
not an automatically approved training dataset.

Aim toward 25,000-50,000 acquired candidates only after this pilot measures
download bytes, class/source diversity and annotation effort. Candidate counts
are not reviewed training counts. A smaller correctly reviewed first experiment
is acceptable; scaling to 100,000+ is conditional on measured benefit.

Sources: [publisher downloads](https://storage.googleapis.com/openimages/web/download_v7.html),
[publisher annotation/evaluation policy](https://storage.googleapis.com/openimages/web/evaluation.html).
The existing broad weights are already Open Images pretrained; collecting more
generic images does not automatically improve recognition.

## Acquisition stages

| Stage | Bounded action | Exit evidence |
| --- | --- | --- |
| 1. Storage and metadata | Check cluster workspace lifetime, capacity/quota and backup route; acquire the listed train metadata | File identities, sizes and source receipts; no image downloads |
| 2. Catalogue and selection | Index metadata on an appropriate CPU Slurm job; inventory all frozen classes; select up to 600 candidates across six domains | Per-class availability, source groups, unsupported annotations, proposed selection |
| 3. Image intake | Fetch only selected IDs, with at most 1 GB total image bytes and 10 MB per image for the pilot | Actual bytes, decoded dimensions, hashes, failures and duplicates |
| 4. Annotation review | Review a representative first 60 images, then the pilot if feasible | Missing-label rate, corrections, rights evidence, reviewer time and unresolved cases |
| 5. Evaluation baseline | Collect separate real footage; annotate and freeze validation/test by camera/site/session | Reproducible baseline scores and measurable domain gaps |
| 6. Controlled expansion | Acquire batches of up to 5,000 candidates toward the larger planning range | Updated coverage, review capacity, storage accounting and leakage checks |
| 7. Training readiness | Export an immutable reviewed bundle, or validate an explicit alternative for partial supervision | Honest review flags, pinned labels/hashes, locked evaluation and a compute budget |

The pilot policy is [general-intake-pilot.json](../training/general-intake-pilot.json).
It uses the current selector's round-robin categories. Domain counts and class
quotas are targets, not guarantees; catalogue supply, overlap and rejection can
reduce the result. This policy neither approves training nor resolves missing
labels. It retains the smoke scope unchanged.

## Metadata sources and vocabulary

[openimages-train-sources.json](../training/openimages-train-sources.json) pins
the official URLs and observed HTTP sizes. The train image/attribution file,
train boxes and boxable human-verified image labels total **3,273,620,121 bytes**
(about 3.27 GB / 3.05 GiB). These are CSV data, not photographs. Additional
catalogue, temporary files and exports require more space.

The current V7 download page links V6 boxes and V5 boxable image-level labels;
use those linked releases as supplied, recording each source's version. Preserve
positive, verified-negative and unknown class states distinctly. Verified
image-level labels are useful evidence, but are not a substitute for missing
boxes or an implementation of partial-label training.

The official V7 boxable class CSV has a header and 601 data rows. Its MID set
matches our existing headerless normalized classes.csv. Nine display names
differ (for example publisher Fixed-wing aircraft vs frozen Airplane). Join by
MID and reuse the frozen mapping; never reorder the model labels from a new
publisher name list. The current catalogue importer expects the normalized
headerless class file, not the official CSV directly.

Store raw files in a new ignored directory, such as
output/training-general-v1/source-metadata/. Record URL, retrieval time, length
and SHA256. The observed sizes are not publisher checksums. Record local hashes
as provenance; do not describe them as independent publisher verification.
Existing smoke files and downloaded cluster results remain immutable.

## Image selection and coverage

Start from the six existing domains: people/transport, home/furniture,
kitchen/food, electronics/work, personal/outdoor objects, and animals.
The pilot's 52 anchor categories initiate acquisition; they do not define the
entire product vocabulary. Inventory and progressively cover the other classes.

Balance **independent sources and useful conditions**, not only equal class
counts. Track images, boxes and independent groups per class/domain; small
objects, occlusion, RGB low light, blur and fox/dog confusion are cross-domain
evaluation slices. Retain ordinary daylight examples and reviewed negatives.
Absence of a box is not proof of a negative image. Objects outside the model
taxonomy remain outside it unless adapter/vocabulary work is explicitly done.

Download from the publisher's CVDF image mirror by selected split/ID. Preserve
image IDs, original landing URLs, authors, image terms and box provenance.
Use actual streamed byte limits, decode checks and resumable acquisition receipts.
Downloaded failures must remain visible, rather than silently replaced in the
selection. Download pixels once; keep annotations separately.

## Review and incomplete annotations

This is the main readiness gate. The current standard YOLO runner has no
verified class-specific ignore mechanism. For a full-head ordinary loss, a
review confined to the chosen anchor class is insufficient: other visible
in-vocabulary objects can otherwise become false background supervision.

For the first reviewed pilot, inspect the whole image, retain/correct publisher
boxes and add every relevant visible in-vocabulary instance under a documented
taxonomy and hierarchy policy. Define box boundaries, truncation/occlusion,
minimum resolvable size, ambiguous classes and overlapping parent/child labels.
Flag uncertainty; reject or hold difficult-to-complete images instead of guessing.
Group-of, depiction, inside and unknown flags need an explicit policy. Exclude
unsupported cases initially; do not silently convert a crowd to one ordinary box.

Model-generated suggestions may accelerate review. They remain suggestions:
inspect missed objects as well as predicted boxes, and record reviewer identity,
time, changes and approval. AI labels cannot self-certify label completeness.
Measure the first 60 images across all six domains before projecting labour.
At 2-5 minutes per image, 25,000 images would require about 833-2,083 reviewer
hours; that is an illustration, not a measured time estimate for this project.

If full review is infeasible, choose a separate, tested partial-supervision
implementation with positive/negative/unknown masks and box-assignment handling,
or a source with suitable complete labels. That changes the training pipeline
and requires verification. Do not bulk-enable complete_target_classes or
rights_verified to bypass the existing gate. Sampling audits do not certify
every unreviewed image.

Retain image license/attribution evidence and review rights for the intended
use. Annotation terms and image terms are different records. Existing software
and model terms remain a separate project decision.

## Real footage and synthetic data

Collect separate permissioned recordings from varied rooms, desks, kitchens,
streets/outdoor settings and animal scenes. Record camera/site/session, lighting
and recording identity. Avoid uploading private footage to annotation services
without an explicit choice; an annotation tool can be assessed separately.

Extract a sparse, diverse selection rather than thousands of adjacent frames.
All frames from a recording/session stay in one partition. Hold an independent
test apart from training acquisition; public evaluation photos alone do not
establish deployment independence from the pretrained model's data.

Real RGB low light and infrared are distinct modalities. Brightness statistics
do not label night scenes. Start with real data; later test restrained exposure,
blur, scale and noise augmentation on training only. Generated imagery can be
a tagged experimental supplement but cannot establish real-world accuracy.
Keep supplied generated clips as separate stress examples.

## Splits, evaluation and release gates

Train teaches the model; validation chooses checkpoints/thresholds; the locked
test measures the selected candidate. Keep camera/site/session/author groups
together and screen exact hashes, perceptual duplicates, crops and video
neighbours across all sources, including existing reference and smoke images.
The current 60/20/20 author hash split is a tooling default; do not mistake it
for a reviewed deployment split or promise those exact proportions at scale.

Freeze class IDs, review conventions, split manifest and content hashes.
Keep test imagery out of training and threshold selection. Baseline against the
unchanged broad Open Images model and YOLOX-S's relevant people/vehicle classes.
Report per-class/domain precision, recall, AP and support counts, hard-slice
confusions, negative-footage false detections per minute and native speed/memory.
Use reviewed validation to define improvement/regression targets before training.
Report sparse classes as insufficiently evaluated rather than hiding them in an
aggregate. Official Open Images scoring needs its own hierarchy/unknown/group
handling; ordinary COCO/YOLO mAP on partial labels is not interchangeable.

After a candidate beats the frozen baseline, verify ONNX labels/numerical parity
and the accepted analyse/review/save/reopen/CSV workflow. RF-DETR comparison uses
the same reviewed evidence later, with its own explicit native adapter.

## Tooling work before scale

Current tools remain appropriate for a small controlled pilot, with limitations:

- prepare() caps max_images at 10,000, so a 25,000+ request cannot be passed as
  one policy without a deliberate change or a verified batching/merge workflow.
- Metadata-only selection cannot currently be fetched later from that same
  output directory. Implement persisted-selection acquisition and safe restart.
- Acquisition writes its final manifest only at the end. Add per-image receipts,
  bounded retries and failure/budget accounting before larger downloads.
- Pairwise perceptual duplicate checks and repeated class queries need scaling
  work and cross-dataset checks. A difference hash is only an initial screen.
- The catalogue lacks image-level supervision and inside flags; the review gate
  is a boolean declaration, not an annotation-review interface or audit trail.
- The generated manifest currently says publisher validation even for a train
  catalogue; fix that provenance description before new reviewed publication.
- The exporter keeps a YOLO image copy and another COCO image copy. Budget both,
  plus acquired originals, checkpoints, metadata and a backup.

Do not raise a limit and call the smoke tooling production-ready. Keep changes
modular, retain immutable bundles and verify actual restart/budget/leakage cases.

## Immediate commands

Run these in the **Linux cluster SSH terminal** to inspect storage:

```bash
cd "$(ws_find frametrail)/FrameTrail"
ws_list
df -h .
du -sh . output .venv
```

df reports filesystem space shared with other users, not necessarily your own
quota. Confirm any account/project quota and a recoverable backup destination
before the image acquisition batch. C: had about 62.4 GiB free at this inspection.
At an illustrative 0.5 MB per JPEG, 25,000 originals use about 12.5 GB; originals
plus the current two export copies use about 37.5 GB before metadata, SQLite,
checkpoints or backup. Actual bytes will be measured during the pilot.

After storage is resolved: acquire the pinned metadata, index it through CPU
Slurm, inspect the all-class inventory, then review the persisted 600-image
selection before fetching. Heavy catalogue/processing work runs on compute
nodes. Metadata/download partition and time/memory requests must be chosen from
the user's permitted CPU queues; do not invent an account entitlement.

## Prepared metadata job (4 October 2026)

The user's quota check reported 8.569 GiB used, a 40 TiB soft allowance and a
44 TiB hard limit on /pfs/work9. The existing project output used 99 MiB and
.venv used 7.3 GiB. curl was available. cpu_il was listed with idle nodes;
successful submission and compute-node network access remain unverified.
The workspace listed expiry on 3 November 2026 with three extensions available.

[Metadata runner](../scripts/acquire-cluster-metadata.py) and
[CPU job](../training/run-cluster-metadata.sbatch) are prepared. The job requests
one CPU, 8 GiB RAM and at most two hours on cpu_il. It reuses the existing .venv,
acquires five listed metadata/reference files (3,273,718,476 bytes total),
verifies the frozen class mapping, builds the train catalogue with the existing
importer and writes a full-class inventory. It downloads no photographs and
starts no training. Human image-level labels are retained as a raw file but are
**not yet indexed or used for supervision**.

Interrupted HTTP transfers remain as .part files and resume only when the HTTP
validator and exact byte range match. Completed files are reused only when their
receipt, size and SHA256 agree. This is local integrity/provenance, not a
publisher-provided checksum. The byte cap applies to stored source payloads;
network retransmissions may consume additional bandwidth. Do not run two
metadata preparation jobs concurrently against this directory.

The small transfer archive is
output/training-general-v1/frametrail-metadata-tools-v1.tar.gz. It contains the
runner, job, source specification, pilot policy and existing normalized class
file only; no environment, images, weights, credentials or private results.
Archive extraction goes to a new metadata-tools-v1 directory beneath
output/training-general-v1. --keep-old-files preserves previously extracted
tools; a repeated extraction should be investigated rather than forced.

Windows PowerShell (use the campus network/VPN used for SSH):

```powershell
$taskLocalRoot = 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskClusterUser = Read-Host 'Your cluster SSH username'
scp "$taskLocalRoot\output\training-general-v1\frametrail-metadata-tools-v1.tar.gz" "$taskLocalRoot\output\training-general-v1\frametrail-metadata-tools-v1.tar.gz.sha256" "${taskClusterUser}@uc3.scc.kit.edu:~/"
```

Linux cluster terminal (stop on any error):

```bash
cd "$HOME"
sha256sum -c frametrail-metadata-tools-v1.tar.gz.sha256
cd "$(ws_find frametrail)/FrameTrail"
mkdir -p output/training-general-v1
tar --keep-old-files -xzf "$HOME/frametrail-metadata-tools-v1.tar.gz" -C output/training-general-v1
sbatch output/training-general-v1/metadata-tools-v1/run-cluster-metadata.sbatch
```

Record the actual submission ID. Check squeue -j JOBID, then
frametrail-metadata-JOBID.log and
output/training-general-v1/catalogue-JOBID/preparation.json.
Require Slurm COMPLETED with exit code 0, report status completed, the catalogue
file and inventory.json before saying indexing succeeded. Inspect counts and
zero-coverage classes before persisting/fetching the 600-image selection. A
network, wall-time or metadata failure needs its actual log; it does not warrant
reinstalling the already verified environment or using a GPU queue.

### Observed catalogue completion and selection handoff

The user's supplied log/report confirms job **7447265** completed with Slurm
exit code 0 in 5 minutes 18 seconds and preparation status completed. The train
catalogue contains 1,743,042 image records and 14,610,229 boxes. Of 601 raw labels,
599 have boxes; all 597 canonical app categories remain in the model contract.
The SQLite SHA256 is
bd42dbb1129406c16cda37401670ecba04d6d956cde0071ab79de6190162e78d.
These are indexed metadata counts, not acquired photographs or review approval.

[Selection job](../training/run-cluster-selection.sbatch) verifies that source
catalogue and pilot policy, logs the zero-box classes, and uses the existing
metadata-only sampler. It excludes old smoke image IDs, requests one CPU,
4 GiB RAM and 30 minutes on cpu_il, and saves selection.json plus a summary.
Its six-domain gate must pass; per-anchor shortfalls remain visible. It does
not fetch photographs, approve rights/annotations or change the model vocabulary.

Transfer only that script to cluster home as frametrail-selection-v1.sbatch.
From the existing Linux project directory, submit:

```bash
sbatch --export=ALL,FT_CATALOGUE_JOB=7447265 "$HOME/frametrail-selection-v1.sbatch"
```

Use the actual new ID for frametrail-selection-JOBID.log and
output/training-general-v1/pilot-selection-JOBID/selection-summary.json.
After Slurm/report completion, inspect domain counts, anchor shortfalls and
selection identity before fetching the persisted IDs. The previous catalogue
and acquired metadata remain intact and need no repetition.

### Selection v1 findings and all-anchor revision

Job **7448416** completed with exit code 0 in 46 seconds, using catalogue
7447265. The downloaded three JSON outputs passed local hash/count/policy checks:
600 unique publisher-train IDs, no overlap with the 96 smoke images, all six
domains, but only 50/52 requested acquisition anchors. Selection SHA256:
f09990778704c7e51d54295fa88e0b39da0a840f77cc7fa6de01a06e16869d15.
People/transport, home, electronics and personal domains each received 96 IDs;
kitchen and animals each received 108. Container and Kitchenware have zero
direct raw box labels; that is distinct from the anchor sampling issue.

The old selector fills 12 slots per anchor and stops at 600 before querying
lantern/balloon. Their absence does not establish eligible-source scarcity.
The new [selector](../scripts/select-balanced-pilot.py) gives every anchor a turn
before repeats, keeps the 600-image cap, counts eligible source IDs for all anchors,
and fails its coverage gate if any anchor is missing or fewer than 600 are selected.
52 times 12 equals 624, so ample supply normally yields 11 or 12 per anchor.
Seven SQLite-only regression tests passed, including source identity, exclusions,
duplicates, eligibility filters, deterministic selection and failure reporting.
These are local tests, not observed success against the complete KIT catalogue.

The small v2 package contains ONLY this selector and its new CPU job. It reuses
the current catalogue, frozen pilot policy, vocabulary and .venv; historical
selection 7448416 stays intact. Run in Windows PowerShell:

```powershell
$taskLocalRoot = 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskClusterUser = Read-Host 'Your cluster SSH username'
scp "$taskLocalRoot\output\training-general-v1\frametrail-selection-tools-v2.tar.gz" "$taskLocalRoot\output\training-general-v1\frametrail-selection-tools-v2.tar.gz.sha256" "${taskClusterUser}@uc3.scc.kit.edu:~/"
```

Then in the Linux cluster terminal (once; stop on any error):

```bash
(
  set -e
  cd "$HOME"
  sha256sum -c frametrail-selection-tools-v2.tar.gz.sha256
  cd "$(ws_find frametrail)/FrameTrail"
  tar --keep-old-files -xzf "$HOME/frametrail-selection-tools-v2.tar.gz" -C output/training-general-v1
  bash -n output/training-general-v1/selection-tools-v2/run-cluster-selection-v2.sbatch
  sbatch --export=ALL,FT_CATALOGUE_JOB=7447265,FT_PRIOR_SELECTION_JOB=7448416 \
    output/training-general-v1/selection-tools-v2/run-cluster-selection-v2.sbatch
)
```

This step subsequently completed as job **7449188** (45 seconds, exit 0; local
artifacts verified). The following inspection pattern is retained for reference:

```bash
cd "$(ws_find frametrail)/FrameTrail"
read -r -p 'New selection v2 job ID: ' task_selection_job
sacct -X -j "$task_selection_job" --format=JobID,State,ExitCode,Elapsed
tail -n 100 "frametrail-selection-v2-${task_selection_job}.log"
cat "output/training-general-v1/pilot-selection-v2-${task_selection_job}/selection-summary.json"
```

Require Slurm COMPLETED/0:0, status completed, coverage_gate_passed true, 600
unique IDs, all 52 anchors, no missing anchors and matching selection SHA256.
Shortfalls below 12 are expected within 600; zero anchors are NOT acceptable
without investigating eligible counts/overlap. This is metadata selection only.
No photos, annotation/rights approval, training run or accuracy improvement is
implied. After coverage verification, acquire these exact IDs with a restartable
bounded downloader, review a first 60 and retain rejection/decode/attribution
receipts before enlarging the reviewed population or launching training.

### First-60 photo acquisition handoff

Selection 7449188 passed with all 52 anchors: 28 anchors have 12 IDs and 24 have
11. Lantern and balloon each have 11; the job reports eligible supplies of 462
and 1,344 respectively. Local verification matched selection, inventory, scope,
prior selection, exclusion manifest, selector source and vocabulary hashes and
reconciled actual IDs/counts to the log/summary. The remote catalogue has not
been retrieved/recomputed locally. No publisher-train photographs are present.

The next module, scripts/acquire-pilot-images.py, is pinned to the verified
selection and first 60 IDs. It supplies bounded/resumable downloads, per-image
receipts, decoded original-image annotations, duplicate review holds and an
offline inspection page. It leaves review flags false and partitions unassigned;
this intake cannot pass the current exporter/training gate. The new CPU job and
manual transfer/retrieval/review commands are in docs/PHOTO_ACQUISITION.md.
The module has been tested locally with fake HTTP and real JPEG fixtures, but
no photograph job or remote download has been submitted or observed yet.
