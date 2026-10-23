# Current FrameTrail state — unified app, 19 October 2026

The user's request to keep all app sections in one window is implemented and packaged. Current package:
C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\native-unified-20261019-v1

Stable normal launcher: C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\Run-FrameTrail.cmd
Stable explicit RF preview launcher: C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\Run-Balanced-Preview.cmd

Preview, Analysis, Playback and Camera share a persistent sidebar and stacked content area. State is retained; Ctrl+1–4 switches sections. Analysis/preparation can continue with a global activity badge; hidden playback pauses; leaving Camera requests stop. Playback has an explicit preparation entry and releases old overlays when its source changes. Shared-window quit honors unsaved partial-analysis Save/Discard/Cancel before stopping all workers. Old source/build packages are preserved.

Verification: 13 selected existing native checks passed, the extended unified-window test passed at normal and simulated 125% Qt scale, full RF cache parity/pause/model-free replay passed, and both packaged smoke launches returned 0. Captures were inspected. Live camera hardware and physical-display/screen-reader behaviour remain unverified. Seven model hashes are unchanged. Core/detector/inference sources are unchanged from the preceding workflow package. Normal default remains YOLOX-S; RF remains the explicit job 7805570 step 100 preview, strict ONNX numerical qualification held, production_adoption=false.

KIT remains down according to the user. Latest data collection submission/completion is unconfirmed. No SSH, retrieval, retry, replacement or submission was attempted. Previously audited arrays 7809335/7818553 remain local and complete. Preserve all qualification, batching and no-retry gates.

Read REPORT.md and FINAL_RECEIPT.json in the current package for evidence. Carry all standing communication/autonomy instructions forward: continue authorized local work without routine permission prompts, and end every response with one concrete project next step and why.

Next step: use the unified Preview → Analysis → Playback flow with a representative project video on the actual display, because local functional and scale checks are complete and real-use feedback can identify the next refinement.

---

## Preserved prior handoff

# Current FrameTrail state — 19 October 2026

The user reports KIT is down indefinitely. No SSH, status, retrieval or submission was attempted during this app-side pass. The newest data collection's submission/completion is unconfirmed; do not assume it finished or create a replacement. Arrays 7809335 and 7818553 were previously retrieved and independently audited locally. Preserve all existing cluster evidence and no-retry policy.

Authorized local video usability/performance work is complete and packaged:
C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\native-workflow-20261019-v1

Use Run-FrameTrail.cmd in that folder for the existing YOLOX-S default; Run-Balanced-Preview.cmd is the unchanged explicit RF preview. Fixes: persistent stopping feedback, bounded preparation preview, elapsed/FPS/approximate remaining time, no label-brush fill leaking into detection boxes, clear cancelled partial-result wording, corrected preparation failure state. All 13 selected existing native checks passed; both workflow diagnostics, exact full-cache overlay/pause/model-free replay checks, and both packaged smoke launches passed. Seven packaged model hashes are unchanged; original source and older package are preserved.

RF CPU inference remains the main measured cost (~98% of sampled detector processing). No inference speedup or new model accuracy is claimed. The user can use the app while KIT is unavailable. Strict ONNX numerical qualification remains held, production_adoption=false, current RF checkpoint remains job 7805570 step 100 (c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3).

Evidence and scope: REPORT.md, FINAL_RECEIPT.json, MODEL_INTEGRITY.json and SCOPE.json in the new folder. Offscreen captures were inspected; physical display/high-DPI/assistive-technology checks remain unverified. Do not repeat the completed model trials or numerical export alternatives without reviewing the detailed earlier evidence below.

Carry all standing communication/autonomy/batching instructions into continuations. End responses with one concrete project next step and why. Continue useful local work without routine approval prompts; do not contact KIT while the outage remains the latest known condition.

Next step: exercise the updated package with a representative project video, because synthetic workflow checks cannot establish real-clip usability. When KIT access returns, check/retrieve the existing data task once using the prepared tools, with no replacement submission.

---

## Preserved earlier model/data handoff

# FrameTrail: audited selector results and the next data move

Retrieval and independent audit succeeded for all four tasks in array 7818553. All 64 validation records were independently rescored; selection was replayed; all best/last model tensors and fixed update schedules were checked. Each best checkpoint contains the unchanged job 7805570 step 100 weights, despite different serialized provenance hashes. All last checkpoints changed only the two allowed billboard rows. The current model remains selected; no new model is adopted.

| Trial | Maximum validation billboard hits | Final measured complete FP | Final unscored predictions | Selected step |
| --- | --- | --- | --- | --- |
| 0 | 5/11 | 1 | 550 | 0 |
| 1 | 5/11 | 0 | 553 | 0 |
| 2 | 6/11 | 1 | 590 | 0 |
| 3 | 7/11 | 1 | 586 | 0 |

The effective unscored cap is 530, from original baseline 525 plus five. The current baseline is 528, so its separate cap is 533; both apply. Every checkpoint with billboard gains exceeded at least the stricter cap. Three final trials also added a measured billboard FP. Unknown predictions are not automatically false positives. Other reviewed classes passed their individual retention counts.

## What the selector actually changed

Post-run CPU inspection of all 20 billboard TRAIN photos confirms that proposal selection changed. At the larger encoder learning rate, the final boxes provided an IoU>=0.5 covering box for 50/54 training targets, compared with 37/54 at the starting checkpoint. Both larger-rate trials changed proposal sets on all 20 photos. The lower-rate trials covered 38/54. This measures training geometry coverage, not detection accuracy or independent generalization. Improving this training geometry did not produce an eligible validation checkpoint.

## Local error and annotation review

All 30 validation photos containing new unknown-scope billboard predictions were visually inspected. Scene triage found 22 non-billboard contexts, seven ambiguous cases and one scene containing an unlabelled physical advertisement. Examples include projected slides, framed art, consumer packaging, laundry notices, shop lettering, road signs and ordinary indoor surfaces. This is posthoc scene triage, not per-box ground truth. No validation labels, original scores or selection gates were changed, and no validation photos entered training.

All 20 positive TRAIN photos were reviewed. Three business-name/direction-board cases were held in a separate local contrast comparison because their category boundary is uncertain. Five Times Square photos account for 28 of the 54 original TRAIN billboard targets, illustrating scene concentration. Original labels and scopes remain preserved.

Twenty-four further existing TRAIN photos were reviewed separately: 12 laundry/household photos support billboard absence across the photo; 12 road-sign photos support negative queries only inside reviewed sign panels. Two road scenes also contain visible advertising boards outside the sign region; those remain unknown. These separate overlays do not mutate the original sealed release.

Four predeclared CPU fits tested expanded negative coverage with original 20 versus boundary-held 17 positive photos, crossed with two training-only teacher-preservation strengths. All four fits preceded any new validation outcome. All 24 new feature caches exactly reproduced the full-model outputs; frozen model state and the source checkpoint were unchanged. Each stored validation prediction set was independently rescored and its gates replayed:

| Fit | Positive policy | Teacher weight | Billboard hits | Measured complete FP | Unscored |
| --- | --- | --- | --- | --- | --- |
| 0 | original20 | 1 | 9/11 | 1 | 635 |
| 1 | original20 | 10 | 6/11 | 0 | 539 |
| 2 | boundary_hold17 | 1 | 9/11 | 2 | 629 |
| 3 | boundary_hold17 | 10 | 5/11 | 0 | 539 |

None qualified. The conservative expanded-data fit reached 6/11 with zero measured FP and 539 unscored predictions, still nine above the effective cap. Repeated development comparisons do not create fresh test evidence. Existing references are consumed and no thresholds/gates were relaxed.

## Next move: bounded data refresh before more training

A sealed CPU-only collection package is ready under the latest standing user authorization. Maximum 240 unreviewed candidates: 120 billboard anchors plus 24 each for traffic signs, washing machines, picture frames, computer monitors and whiteboards. It excludes all 1,931 previously acquired photos and their known author aliases. At most one photo per author alias; prospective train/validation/test quotas are assigned before downloading images or producing model predictions. Missing candidates remain explicit shortfalls, with no silent replacements or category substitutions.

This uses the existing pinned publisher TRAIN SQLite catalogue on KIT, avoiding another large metadata download. The [Open Images documentation](https://storage.googleapis.com/openimages/web/factsfigures_v7.html) distinguishes explicitly verified negative labels from unannotated classes; publisher contrast anchors therefore never establish billboard absence automatically. Every collected photo stays unreviewed and unapproved for training. Source-specific evidence, resolved NSID/alias identity, exact/perceptual duplicates against prior intakes AND all known regression images, scene/session overlap, content and boxes must pass review before any release. Prospective held-out groups remain outside training; no fresh accuracy claim exists yet.

One job on cpu_il, two CPUs, 8 GiB, 45 minutes wall, 2,400 seconds active collection, zero GPUs and no inference/training. Maximum 1 GB of original/partial image bytes and 480 MB source HTML, with existing per-image/decode/source limits. Each image/source is attempted once. Partial data and failures are archived; no retries, requeue or replacement jobs. Scheduler/account evidence and sbatch --test-only precede the single real submission. Account entitlements remain uninspected until authenticated submission.

Package checks passed: nine synthetic selection/source/budget contracts, four safe result-verifier contracts, six inert scheduler/trap cases, final shell syntax, and an upload mock proving that the archive plus start script use one SCP invocation. Archive members were read back and hash verified. No SSH, upload or new submission has occurred. The package is about 190 KiB; no training images/models are uploaded.

Windows PowerShell upload (one authenticated connection for both files):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\billboard-data-refresh-7818553-20261018-v1\Upload-Data-Package.ps1"
```

Then run in the already authenticated cluster terminal:

```bash
bash "$(ws_find frametrail)/FrameTrail/output/frametrail-start-data-refresh-2fb87eec-v1.sh"
```

The cluster start command validates the exact archive and seal, records scheduler/account evidence, checks admission and submits once. Keep that cluster session open for later status checks; it avoids repeated OTP/password logins. Never paste credentials into chat. Model, data and adoption gates remain in force; current default YOLOX-S and explicit native preview are unchanged, strict ONNX numerical qualification remains held and production_adoption=false.

Next step: upload the small collection package, then start it from the existing cluster session, because local diagnosis and package checks are complete and direct KIT authentication is the remaining input.

Latest state: C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\selector-diagnosis-7818553-20261018-v1\CURRENT_STATE.json
