# First-60 photograph acquisition and inspection

Prepared 4 October 2026. Selection **7449188** is verified locally: 600 unique
publisher-train IDs, all 52 requested intake anchors, six domains, no old smoke
ID overlap, matching selection/inventory/input hashes, and Slurm COMPLETED/0:0
in 45 seconds. Its selection SHA256 is
69d67561b87f4efad265f4713a415ff985e7bc551fa01b931c574c1e16d68ef5.
Source catalogue job is 7447265; original selection job is 7448416.

Photo job **7450934 completed** with exit code 0 in 1 minute 7 seconds. All 60
photos and receipts were retrieved and independently checked locally: hashes,
sizes, decode/fingerprints and frozen first-60 membership matched. Originals
total 17,984,698 bytes, with 322 unreviewed publisher boxes. All 52 anchors/six
domains are represented; no failed IDs or exact/simple-dhash duplicate candidates
were found. Manifest SHA256:
a7f1cd4e65482eeae54b691dc24f8d18f6b52cb06e3ca5045ed0801aee0aeea0.
The local inspection page was opened successfully. **Review is not complete and
training remains unapproved.** Do not repeat upload/setup/acquisition steps below;
they are now reproduction/recovery instructions. Continue at the inspection and
review stage. Remaining 540 candidates have not been downloaded.

Local verification: 16 photo tests passed using simulated HTTP, real JPEG
decode/transfer fixtures and a first-60 catalogue fixture; seven selection and
six metadata regression tests also passed. The 10,478-byte transfer archive has
SHA256 51a858c774aeeb34d3d9460695012b0264b83a9fb08de419ccb9cecaf89c9323.
Packaged source identities, Python syntax and LF line endings were checked;
Bash syntax is checked by the cluster command below. These checks do not prove
actual KIT network/download success.

## What happens next

1. Transfer only the small new tools archive plus its checksum.
2. Submit one CPU Slurm job to fetch the first 60 frozen IDs from selection 7449188.
3. Check the actual new job's log and acquisition report, then retrieve photos
   and evidence to Windows before the workspace expires.
4. Open the offline inspection page and record what the first 60 reveal.
5. Decide annotation conventions/correction workflow and review effort before
   extending acquisition to the remaining 540 candidates or larger batches.

This does not run a model, train, export a bundle, edit the desktop application,
approve image rights, approve labels or replace the detector. Full training,
independent camera/site/session evaluation and model adoption remain separate gates.

## Scope and safeguards

The first 60 IDs contain all 52 acquisition anchors. Domain intent counts are
10 people/transport, 10 home/furniture, 10 kitchen/food, 9 electronics/work,
9 personal/outdoor and 12 animals/hard cases. Anchors do not restrict the
application's broader 601-raw/597-canonical taxonomy or establish actual object
support/lighting. No synthetic photos are generated for this stage.

The [runner](../scripts/acquire-pilot-images.py) is pinned to the verified
selection identity and first-60 prefix. It reads the existing SQLite catalogue,
checks policy/vocabulary/exclusions, retains attribution and every indexed box,
and requests CVDF mirror objects by `train/IMAGE_ID.jpg`. This follows the
publisher's [subset-download scheme](https://storage.googleapis.com/openimages/web/download_v7.html)
and [reference downloader](https://raw.githubusercontent.com/openimages/dataset/master/downloader.py).
No fallback request is made to an arbitrary original image URL.

- Stored original/partial image payload cap: 1,000,000,000 bytes.
- Per-image cap: 10,000,000 bytes. With only 60 images, originals can total at
  most 600,000,000 bytes; actual measured bytes may be much smaller.
- JPEG decode cap: 40 megapixels; non-identity EXIF orientation is held rather
  than silently rotating pixels and misaligning boxes.
- At most three attempts per ID per job for transient failures. Missing/invalid
  images remain recorded under the original ID; nothing is silently substituted.
- Per-image receipts record SHA256, HTTP validators, size, decoded dimensions,
  fingerprint and retrieval time. There is no supplied publisher pixel checksum.
- Completed photos are rechecked/reused without another request. Partial
  transfers resume only against the same HTTP identity and exact byte range.
- A killed process may leave an uncommitted chunk; recovery discards that tail
  only after validating its registered checkpoint prefix.
- One OS-held acquisition lock prevents concurrent writers and releases when
  the process exits. Changed completed pixels, plan, inputs or edited manifests
  fail closed instead of being replaced.
- Exact/near duplicate candidates against this intake and the old smoke set are
  review holds, not automatic proof of duplication/independence. The perceptual
  screen is limited; crops, video neighbours and later sources need stronger checks.

The byte cap concerns stored image payloads, not retransmitted network traffic;
small receipts/review metadata consume additional disk space. The job requires
at least 2 GB filesystem free, but that check does not replace account quota.
The previously reported quota/workspace has ample room for this bounded pilot.
The reported workspace expires on 3 November 2026 and has no backup.

## 1. Windows PowerShell: upload the new tools

Use the campus network/VPN used for SSH. Enter OTP/password only in your terminal.

```powershell
$taskLocalRoot = 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskClusterUser = Read-Host 'Your cluster SSH username'

scp "$taskLocalRoot\output\training-general-v1\frametrail-photo-tools-v1.tar.gz" "$taskLocalRoot\output\training-general-v1\frametrail-photo-tools-v1.tar.gz.sha256" "${taskClusterUser}@uc3.scc.kit.edu:~/"
```

The archive contains just the new runner and CPU job. Photos, environments,
weights, credentials, user analyses and historic results are not included.

## 2. Linux cluster terminal: verify, extract and submit

Run once. Stop on any error; do not force overwrite if the tools already exist.

```bash
(
  set -e
  cd "$HOME"
  sha256sum -c frametrail-photo-tools-v1.tar.gz.sha256
  cd "$(ws_find frametrail)/FrameTrail"
  tar --keep-old-files -xzf "$HOME/frametrail-photo-tools-v1.tar.gz" \
    -C output/training-general-v1
  bash -n output/training-general-v1/photo-tools-v1/run-cluster-photo-pilot.sbatch
  sbatch --export=ALL,FT_SELECTION_JOB=7449188 \
    output/training-general-v1/photo-tools-v1/run-cluster-photo-pilot.sbatch
)
```

The [job](../training/run-cluster-photo-pilot.sbatch) requests one CPU, 4 GiB RAM
and up to two hours on cpu_il, using the existing Python 3.12 .venv and Pillow.
No GPU is requested. The HTTP/decode work runs on a compute node, not directly
on the login node. Actual CVDF connectivity/download success on KIT is not yet
verified. Record the NEW `Submitted batch job ...` ID; **7449188 identifies the
source selection, not this new photograph job**.

## 3. Linux cluster terminal: inspect the actual new job

```bash
cd "$(ws_find frametrail)/FrameTrail"
read -r -p 'New photo job ID: ' task_photo_job

squeue -j "$task_photo_job"
sacct -X -j "$task_photo_job" --format=JobID,State,ExitCode,Elapsed
tail -n 100 "frametrail-photos-${task_photo_job}.log"
cat "output/training-general-v1/photo-job-${task_photo_job}/acquisition.json"
```

The intake is kept separately at
`output/training-general-v1/photo-pilot-7449188-first60/`. This stable directory
contains `intake-plan.json`, clean JPEGs in `images/`, per-image `receipts/`,
`manifest.json`, `progress.json`, `review.html` and `review-notes-template.md`.
Each submitted photo job has a new `photo-job-JOBID/acquisition.json` report and
`frametrail-photos-JOBID.log`; repeated attempts never relabel the source job.

Acquisition success requires Slurm COMPLETED/0:0, report `status: completed`,
`photographs_downloaded: 60`, `failed_images: []`, 52 downloaded anchors, intact
image receipts and matching manifest SHA256. `approved_for_training` must remain
false. A vanished queue entry, available HTML page or partial manifest is not
enough. Download completion does not resolve duplicate/review holds.

If partial/transient failures occurred, inspect their actual reasons first.
The same sbatch submission command (without extracting again) resumes the same
frozen intake under a NEW job ID and reuses validated completed photographs.
Do not launch concurrent retries, delete partials, bypass corruption checks,
edit review flags or reinstall the verified environment as a generic response.

## 4. Windows PowerShell: retrieve the pilot and job evidence

Use the new photograph job ID, not 7449188, when prompted below:

```powershell
$taskLocalRoot = 'C:\Users\nazee\Documents\All Modules\FrameTrail'
$taskClusterUser = Read-Host 'Your cluster SSH username'
$taskPhotoJob = Read-Host 'New photo job ID'
$taskRemoteRoot = "/pfs/work9/workspace/scratch/${taskClusterUser}-frametrail/FrameTrail"
$taskResults = "$taskLocalRoot\output\kit-results\$taskPhotoJob"
if (Test-Path -LiteralPath $taskResults) { throw 'Results folder already exists; preserve it and choose a new destination.' }
New-Item -ItemType Directory -Path $taskResults | Out-Null

scp -r "${taskClusterUser}@uc3.scc.kit.edu:${taskRemoteRoot}/output/training-general-v1/photo-pilot-7449188-first60" "$taskResults"
scp "${taskClusterUser}@uc3.scc.kit.edu:${taskRemoteRoot}/frametrail-photos-${taskPhotoJob}.log" "${taskClusterUser}@uc3.scc.kit.edu:${taskRemoteRoot}/output/training-general-v1/photo-job-${taskPhotoJob}/acquisition.json" "$taskResults"
```

This copies the pilot and its small receipts/review files, not the large
catalogue, environments or model weights. SCP does not itself validate image
receipts. Inspect/verify local pixel hashes and report identities before review.
Do not copy over a prior local review directory. A later resumed job gets its
own local results folder, so existing notes remain available.

## 5. Inspect photographs on Windows; record actual review findings

After retrieval and identity checks, use your normal browser:

```powershell
$taskPilot = "$taskResults\photo-pilot-7449188-first60"
Start-Process -FilePath "$taskPilot\review.html"
if (-not (Test-Path -LiteralPath "$taskPilot\my-review-notes.md")) {
  Copy-Item -LiteralPath "$taskPilot\review-notes-template.md" -Destination "$taskPilot\my-review-notes.md"
}
```

Copy the notes template only once; if your notes already exist, keep them.
The standalone HTML uses only local files, includes publisher-box overlays and
clean-image links, and makes no annotation-service upload. It is an inspection
aid, not an annotation editor or approved saved-analysis UI replacement. Photos
remain unchanged. Keep generated manifest/page separate from your review notes;
the downloader preserves the notes template and refuses edited manifests.

For each photo:

1. Confirm the anchor object actually appears and the publisher boxes align.
2. Inspect the ENTIRE image: note all missing/wrong in-vocabulary objects,
   not merely the anchor. Parent/child labels and overlapping boxes need a
   documented taxonomy policy. Do not treat missing boxes as negatives.
3. Record ambiguous classes, unresolved small objects, truncation/occlusion,
   actual RGB lighting and blur. Average brightness is not a night label.
4. Check duplicate holds and source/attribution/rights evidence for intended use.
5. Record reviewer and time spent. Keep uncertain images on hold rather than
   guessing or bulk-approving flags.

All manifest review flags remain false and dataset partitions remain
`unassigned`. Thus the current exporter/training preflight rejects this intake,
even as a smoke export, until a deliberate review/split module publishes a new
appropriate manifest. A publisher-train source split does not automatically
make an image a member of our final training split.

The source catalogue does not index human image-level labels or publisher
IsInside flags. Those are explicitly unknown/unavailable here, not verified
negatives or an ignore-aware training loss. Existing partial supervision is not
ready. Whole-image review, box correction tooling, a clear hierarchy/flag policy,
independent real-footage evaluation and cross-source leakage checks remain work.
Do not turn review booleans on manually to bypass that work.

After first-60 inspection, use the observed download sizes, holds, missing boxes
and reviewer time to choose the correction workflow and next acquisition batch.
Only after review capacity and label suitability are established should the
remaining pilot or 25,000-50,000 planning range be acquired. Larger candidate
counts alone do not establish useful training or improved accuracy.
