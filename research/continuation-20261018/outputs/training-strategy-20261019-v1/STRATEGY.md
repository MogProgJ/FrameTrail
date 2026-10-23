# FrameTrail fine-tuning: change the experiment, not the iteration count

19 October 2026. Training strategy is the primary task; app work is secondary.

The immediate recommendation is to stop sweeping the same small billboard training set. Build a reviewed, scene-diverse data release, then compare the two existing trainable-head methods with two sampling seeds each. More training time, a larger head or a larger backbone is not yet supported by the evidence. This is a conditional experiment design, not a sealed or submitted training package.

The product objective is useful detections on users' videos with few false alarms, retained existing categories, and practical local playback. A training loss reduction, a successful cluster exit or an extra billboard hit does not establish that outcome.

## What the evidence says

| Question | Evidence | Consequence |
| --- | --- | --- |
| Have we exhausted the current method? | The ledger records 31 previous billboard candidate/control configurations across eight families, including eight completed cluster tasks. None displaced the current checkpoint. These reused development data; they are not 31 independent replications. | Stop additional learning-rate, region-weight and update-count sweeps on the same data. |
| Can the frozen main classifier recover every target? | New TRAIN-only one-to-one geometry analysis covers 37/54 targets at IoU >= .5. The actual training matcher also finds those same 37 good matches; 15 assigned boxes have IoU < .35. | A classifier-only update cannot repair the remaining fixed box geometry. This check found no matching bug; it does not prove every part of training is correct. |
| Can proposal selection improve geometry? | Earlier audited selector trials at encoder LR 3e-5 provide a covering box for 50/54 TRAIN targets, versus 37/54 at baseline. The lower rate covers 38/54. | Retain the two-head method as a controlled comparison. Geometry improved on TRAIN, while validation eligibility still failed. Frozen box weights do not mean fixed box outputs when selected proposals change. |
| Is more classifier capacity the answer? | Eight new fixed CPU fits compared linear and 32-unit nonlinear probes in four identity-disjoint TRAIN folds. Mean query AP was .7641 versus .7580. Both fit positive training queries; the nonlinear probe's held-fold positive recall ranged from 20% to 100%. | No consistent ranking advantage justifies adding a deployable MLP now. This is an exploratory diagnostic, not proof that no better representation could help. |
| Is the data sufficiently diverse? | Only 20 positive TRAIN photos contain 54 billboard targets; five Times Square photos contain 28 of them. Three original photos have category-boundary uncertainty. | Scene concentration and ambiguous supervision are credible bottlenecks. More presentations of these photos add optimization, not independent visual diversity. |
| Do publisher anchors match our task? | New visual triage of 13 unused local anchors found one clear advertising-board scene, eight boundary holds and four non-target anchor contexts. | Publisher class labels cannot substitute for our operational definition. This is a biased residual pool, so its counts do not estimate publisher label purity. No photo or label was cleared by this triage. |
| Is the regression gate merely obstructing learning? | Improving selector checkpoints exceeded the unchanged unknown-scope budget; some added measured false positives. Prior scene triage found real confuser contexts as well as ambiguity and an unlabelled advertisement. | Keep the gate. Unknown predictions are not automatically false positives, but removing the gate would hide changed behaviour without adequate annotations. |

The current RF checkpoint remains job 7805570, step 100, SHA-256 `c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3`. No diagnostic produced an app model or changed the release.

### Limits of the new local tests

The capacity diagnostic used 15 positive photos with 35 geometry-covered queries and 47 explicitly absent TRAIN photos. Two of the 17 boundary-cleared positive photos supplied no covered query and therefore could not participate in that probe. Each absent photo was evaluated at all 300 queries. Training sampled 32 high-baseline-logit and 32 other queries per absent photo, with equal photo mass and balanced class mass. Scaling was fit inside each training fold. There were 160 fixed AdamW updates per fit, no tuning, and no deployment checkpoint saved.

At a binary probe threshold of .5, the linear probe recovered 35/35 held queries and alarmed on 46/47 absent photos; the nonlinear probe recovered 26/35 and alarmed on 9/47. These are **uncalibrated query diagnostics**, not app precision, detector false-positive rates or mAP. A lower alarm rate with lower recall does not establish a better operating point. Identity-disjoint folds can still share scene content, and the baseline used to select hard queries has prior development history. No validation/test images or caches were read for these new fits. A separate plain-Python audit recomputed the stored metrics and fold separation.

## The hypotheses, and how we will reject them

| Hypothesis | Current support | Next discriminating observation | Stop or change if it fails |
| --- | --- | --- | --- |
| H1: ambiguous, incomplete and concentrated supervision drives billboard confusion. | Small positive pool, repeated scene content, boundary cases and confuser errors. Plausible, not causally established. | A fresh reviewed release improves fixed-budget validation results in both sampling seeds without extra reviewed false positives or retention failures. | If TRAIN improves but fresh validation does not, stop the same family; do not buy more updates. Review TRAIN confusers and scene coverage. |
| H2: frozen query selection limits recoverable objects. | 37/54 baseline box coverage; two-head training reaches 50/54 on TRAIN. | Compare main-only versus main-plus-selector heads on exactly the same new release and paired sample schedules. Record geometry coverage separately from detections. | If both have adequate geometry but poor recognition, do not unfreeze box layers. If only selector improves TRAIN geometry and alarms increase, selection remains unqualified. |
| H3: a nonlinear head is necessary. | The fixed nonlinear probe fits TRAIN closely but has no mean held-fold query-AP advantage and unstable recall. | No new GPU test now. Revisit only after stronger data and a repeatable TRAIN-group advantage at a fixed operating criterion. | No deployment architecture change based on training fit or a convenient threshold. |
| H4: implementation/optimization failure explains the wall. | Assignment sanity passes; both tiny probes fit training positives. Prior cached/full-forward parity and audited schedules passed. | New release preflight must replay step zero, scoped loss masks, exact sampling, and frozen-state invariants before training. | On a mismatch, stop before GPU training; fix and preserve the failed evidence. Passing these checks does not prove global correctness. |

## Data comes before the next training package

1. Preserve the existing release, development scores and consumed regression sets. Existing validation/test photos must never become TRAIN confusers. The 13 newly triaged local photos are TRAIN-only review candidates, not fresh evaluation evidence.
2. Retain the frozen meaning: **large physical advertising boards; distinguish traffic signs and shop lettering**. Record examples and boundary holds before predictions. Motel names, directories, construction slogans and shop-service panels remain held when the strict category is unclear. Do not silently broaden the task to improve results.
3. For each new eligible photo, resolve source/rights evidence, author aliases, SHA and perceptual duplicates, scene/session overlap and prospective split. Keep all views of a scene/session and all known linked identities in one role. Compare against all previous intakes and all known regression images, not just the current 965-photo release.
4. Exhaustively annotate in-scope billboard instances on an eligible positive photo, or explicitly review billboard absence over the whole photo. A traffic-sign/monitor/whiteboard anchor is **not** a billboard absence label. Ambiguous photos stay held. Other object categories remain unknown unless independently reviewed; never turn a partially annotated multiclass image into global background.
5. Freeze the new split and label hashes before model predictions. A dedicated fresh validation role is for selection. Keep a separate fresh test role inaccessible to training and checkpoint selection. Assistant-only review limitations must remain explicit; neither a checksum nor this plan substitutes for semantic or rights review.

Open Images explicitly distinguishes verified-negative classes from unannotated classes; the latter cannot simply become negatives. Its publisher taxonomy also does not define FrameTrail's narrower operational boundary. [Official annotation documentation](https://storage.googleapis.com/openimages/web/factsfigures_v7.html).

Minimum pilot entry counts, chosen as engineering gates rather than statistical power guarantees:

| New role | Clear positive photos | Whole-photo absent photos | Diversity minimum |
| --- | --- | --- | --- |
| TRAIN additions | 30 | 30 | At least 20 positive scenes and 20 absent scenes; no more than two photos per scene |
| Fresh validation | 12 | 20 | One photo per scene; no scene/identity overlap with any other role |
| Fresh test | 12 | 20 | One photo per scene; no scene/identity overlap with any other role |

For absent TRAIN controls, cover shop/business lettering, traffic/information signs, indoor frames/screens/boards, and household/laundry contexts, with at least five reviewed photos in each family. These are TRAIN design strata, not a reason to relabel anything in validation. Counts alone cannot guarantee performance; these small curated held-out sets support a bounded pilot, not broad real-world precision claims. Any shortfall blocks training; do not substitute ambiguous photos or silently lower the counts.

The existing CPU collection package can acquire up to 240 **unreviewed** candidates. Its outcome and even latest submission are unconfirmed while KIT is down. Raw collection quotas do not guarantee enough eligible positives/negatives. Do not submit a replacement or count unreturned photos as data. Recover its existing state when access returns, then review the results. If the fresh collection is too small or too ambiguous, record the shortfall and redesign acquisition before another training run.

## Next bounded comparison, conditional on data readiness

Four scientific conditions: two methods crossed with two **sampling** seeds. The two frozen-selector controls can use exact-layout feature caches locally on CPU; only the two changing-selector trials need GPUs. All start from the same selected checkpoint; a fixed initialization seed alone would not create useful replication for these existing rows.

| Trial | Method | Sampling seed | Execution | Trainable parameters |
| --- | --- | --- | --- | --- |
| 0 | M0, frozen selector | 17 | Local CPU cache control | Main classifier billboard row 133 only |
| 1 | M0, frozen selector | 29 | Local CPU cache control | Main classifier billboard row 133 only |
| 2 | M1, selector adaptation | 17 | GPU array task 0 | Main and encoder-proposal classifier billboard rows 133 only |
| 3 | M1, selector adaptation | 29 | GPU array task 1 | Main and encoder-proposal classifier billboard rows 133 only |

Main LR 1e-4, encoder LR 3e-5 for M1, AdamW with zero weight decay, no AMP, joint active-gradient clip .1. Use the pinned runtime and resize512 preprocessing. Backbone, transformer and box-regressor parameters/buffers and all other classifier rows remain bitwise frozen. The M1 dense encoder objective remains the existing scoped geometry-matched IA-BCE objective at weight1. No MLP, new backbone or box-regressor unfreezing is included.

Each update presents four photos: one fresh TRAIN positive, one boundary-cleared original TRAIN positive, one fresh explicitly absent TRAIN control, and one original explicitly absent TRAIN control. Cycle scene groups fairly before repeating a scene and freeze schedules per seed; pair the same schedule across methods. Maintain original scopes on original photos. Fresh positive photos may supervise unmatched billboard queries negative only when billboard completeness has actually been reviewed. Other classes remain scoped. Original held boundary photos stay excluded from this new TRAIN pool; their historical labels are preserved.

This compares the methods on a changed data/sampling treatment. It does **not** cleanly isolate the causal effect of new data from every change in the historical recipe. CPU/GPU optimizer arithmetic is also an implementation difference; no bitwise cross-device trajectory claim is made. Use one pinned CPU Torch reference scorer for all selection outcomes, with cached replay only where exact full-layout parity is established. New caches must replay full-forward outputs; never trim GEMM layouts to save space. GPU-side scores, if collected, are diagnostic. We prefer paired seeds over additional learning rates because stability matters more than finding another lucky setting. Resolve and verify all loss normalization, cache parity, common scoring and schema details against pinned source and small TRAIN fixtures before sealing a runnable package.

Budget: max 1,500 updates/condition, 6,000 total, of which only 3,000 require GPU training. Local controls use two CPU threads, run sequentially and cap at 1,800 active seconds each. Each GPU task caps at 1,800 active seconds including common CPU-reference validation, plus at most 480 seconds for finalization. Request at most one A100, two CPUs and 8 GiB per task, 45 minutes wall, array `0-1%2`. At most two concurrent GPUs and **1.5 allocated GPU-hours** across the array, below the previous envelope. If common scoring cannot finish within budget, preserve the partial result rather than extending or switching the selection device. A timed-out/partial condition is not a complete replicate. No retries, replacements or requeues. Live authenticated scheduler/account evidence and admission checks must precede any submission; the outage means those entitlements are currently unverified. This document is not a launch command.

Validate only at steps 0, 100, 250, 500, 1,000 and 1,500: 24 planned records across four tasks, including baselines. Extra validation points and longer runs would add selection pressure before answering the method/data question.

## Freeze success and failure rules before launching

- Step zero must reproduce pinned original/current retention scores. Preserve the original per-class nondecrease/nonincrease guards against **both** baselines. On the existing development set, unknown predictions remain capped at 530 (original 525+5); current 528+5 does not replace the stricter cap. No threshold or annotation edits after observing outcomes.
- Freeze the design and new labels first, then compute current-checkpoint TRAIN/validation baselines locally once. If fresh validation has fewer than three missed known targets, the declared gain is impossible: record that result and do not launch this training comparison or swap in harder validation photos. Fresh test remains inaccessible to predictions.
- Decode stays confidence .35, NMS IoU .45, matching IoU .5, top pairs300 and maximum detections100. Score fresh complete-scope validation separately from the consumed development set.
- A seed qualifies only if an eligible checkpoint gains at least three fresh-validation known billboard hits over the current checkpoint, with no increase in fresh-validation billboard false positives, and passes every original retention guard. This is a predeclared pilot effect threshold, not a significance claim.
- A method proceeds only if **both seeds** qualify. Rank eligible checkpoints by fresh complete-scope billboard F1, then hits, then fewer false positives, then earlier step. Rank candidate seeds/methods by that validation rule with lower trial index for exact ties. Freeze the single winner's checkpoint and prediction-code hashes before fresh test. No test-based seed/checkpoint reselection.
- If no method is stable across seeds, stop. Record TRAIN fit, geometry, loss and fresh-validation confusions; do not extend to 3,000 updates or add an automatic sweep. If TRAIN fits and fresh validation fails, treat it as a generalization/data result. If loss-mask/parity/invariance checks fail, treat it as an implementation failure. If geometry is the remaining bottleneck after credible data, design a separate bounded adaptation experiment rather than silently unfreezing more layers.
- Run known regression and the locked fresh test once for the chosen winner; either can veto it. A failed winner does not authorize testing the runners-up against the same fresh test. Record uncertainty and scene counts alongside hits/false positives.
- ONNX numerical qualification, CPU latency/memory and app workflow qualification are separate release gates. Existing numerical hold remains: equal decoded counts/classes did not eliminate the recorded raw/score deviations. A scientific improvement does not waive export qualification. Default app stays YOLOX-S; RF remains explicit preview; production adoption remains false.

Complete both CPU controls and their cache audits locally before admission to the single two-task GPU launch; include their frozen receipts in the package. The one launch/upload should include bounded automatic preflight, TRAIN geometry/loss diagnostics, validation selection, frozen-state auditing, result hashing and the locked-winner regression/fresh-test follow-up across all four scientific conditions. Step-zero outcomes reuse pinned scores when applicable. Keep failed evidence. CPU export/parity follows locally only for a scientifically eligible winner; do not reserve another speculative GPU grid. No new training package can be sealed until the actual reviewed release exists.

Billboards are the immediate mechanism test, not the whole accuracy roadmap. Washing-machine recall also remains an unresolved product target. Review its newly collected candidates in the same intake, but do not spend another training job before measuring its own TRAIN geometry, scopes and fresh scene coverage. Reuse the successful diagnostic/selection protocol class by class; any broader adaptation needs explicit replay and retained-class evaluation. If a genuinely useful fresh-data model is incompatible with a frozen legacy guard, surface that consequential conflict for a decision rather than silently relaxing the guard.

## Secondary app work: remove cost before adding decoration

The current app payload is 731,418,828 bytes. Seven bundled ONNX models account for 481,562,612 bytes (65.8%). Optional models and GPU runtimes are the first packaging candidates, not evidence that every large DLL is disposable. Codec and camera dependency loading must be checked before removing runtime libraries.

The next app pass should establish the minimum model set needed for the actual project categories, then build a reversible lean CPU default with optional model/backend packs. YOLOX-S being the default does not establish that it covers billboard/washing-machine requirements; do not remove category coverage to reduce bytes. Keep research checkpoints and receipts outside the distributable, preserve the existing package, and measure launch time, memory, package bytes and a real video flow before claiming speed gains. Removing unused files reduces distribution size; it does not automatically accelerate inference. A small built-in Quick Guide, searchable section jump and visible shortcuts can improve discovery without a new dependency. Prioritize open video -> preview -> analyze -> review/playback -> export, and retain working camera/navigation only where they support that flow. Avoid speculative panels, dashboards and decorative widgets.

No app files or model weights were changed during this training-strategy pass. Existing model inference is the dominant measured RF processing cost, so UI pruning alone cannot make the RF preview real-time.

## Evidence and execution state

- `DIAGNOSTIC_PLAN.json` was fixed before the new TRAIN-only fits.
- `ASSIGNMENT_DIAGNOSIS.json`, `CAPACITY_DIAGNOSIS.json`, `FOLDS.json`, `INPUT_AUDIT.json` and stored query predictions record the local checks.
- `INDEPENDENT_AUDIT.json` recomputes metrics without the training library.
- `EXPERIMENT_LEDGER.json` links previous receipt paths and hashes rather than erasing failed history.
- `LOCAL_REVIEW_QUEUE.json` and `LOCAL_SCENE_TRIAGE.json` preserve source/image hashes and all unresolved clearance flags.
- `EXPERIMENT_DESIGN.json` records the conditional matrix and bounds in machine-readable form.
- The readiness checker is an additional planning screen, not a substitute for the existing authoritative source, release and runtime guards.

No cluster contact, new cluster submission, validation/test fitting, app integration or model adoption occurred. The remaining training blocker is access to genuinely reviewed fresh data, not a missing approval for another sweep.

Next step: recover the existing data-collection state when KIT is available and complete the frozen source/scene/box review, because that is the missing input needed to make the paired experiment informative.
