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
