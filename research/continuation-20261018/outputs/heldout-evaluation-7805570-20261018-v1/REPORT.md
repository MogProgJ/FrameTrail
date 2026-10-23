# Held-out evaluation: job 7805570, selected step 100

**Decision: eligible-for-separate-export-parity-and-performance-gates.**

The checkpoint selected on validation was frozen before these measurements. Both pinned baselines were evaluated with the same fixed preprocessing, decoder, thresholds, and source references. No other checkpoint was considered after scoring.

## Primary held-out evidence

| Reference | Model | Complete TP / FP / FN | Partial known hits / targets | Unscored predictions |
|---|---|---:|---:|---:|
| heldout_photos | original_baseline | 23 / 3 / 15 | 79 / 221 | 686 |
| heldout_photos | continuation_baseline | 23 / 3 / 15 | 79 / 221 | 686 |
| heldout_photos | candidate | 23 / 3 / 15 | 82 / 221 | 686 |
| reserved_video | original_baseline | 30 / 3 / 25 | 7 / 30 | 44 |
| reserved_video | continuation_baseline | 30 / 3 / 25 | 7 / 30 | 44 |
| reserved_video | candidate | 30 / 3 / 25 | 7 / 30 | 44 |

Complete-scope FP counts apply only where completeness or absence was explicitly reviewed. Partial known-positive recall does not establish precision. Unknown predictions are unscored, not false positives.

## Priority classes on the 130 held-out photos

| Class | Original baseline hits / targets | Continuation baseline hits / targets | Candidate hits / targets |
|---|---:|---:|---:|
| cat | 23 / 23 | 23 / 23 | 23 / 23 |
| dog | 15 / 19 | 15 / 19 | 15 / 19 |
| billboard | 0 / 19 | 0 / 19 | 0 / 19 |
| washing machine | 0 / 15 | 0 / 15 | 3 / 15 |

The washing-machine denominator is 15 known targets in seven held-out photos; the billboard denominator is 19 known targets in five photos. Their positive photo scopes are partial, so these hit rates cannot establish class precision. Each class also has seven explicitly absent photo scopes. The reserved video contains no positive cats, dogs, billboards, or washing machines; it checks absence and other-class retention, not positive video recall for these four classes. Billboard and washing-machine absence is established on 20 of its 24 frames. REFERENCE_COVERAGE.json records the exact coverage.

## Retention decision

Against **original_baseline**:

- heldout_photos: PASS
- reserved_video: PASS
- internal_regression: PASS
- old_video: PASS
- recent_video: PASS
- scale_video: PASS

Against **continuation_baseline**:

- heldout_photos: PASS
- reserved_video: PASS
- internal_regression: PASS
- old_video: PASS
- recent_video: PASS
- scale_video: PASS

Primary known-positive hits versus original_baseline: **139 → 142**; strict gain PASS.

Primary known-positive hits versus continuation_baseline: **139 → 142**; strict gain PASS.

## Older regression evidence

| Reference | Original TP / FP / FN; partial hits | Continuation TP / FP / FN; partial hits | Candidate TP / FP / FN; partial hits |
|---|---:|---:|---:|
| internal_regression | 4 / 0 / 5; 5 | 4 / 0 / 5; 5 | 4 / 0 / 5; 5 |
| old_video | 33 / 1 / 44; 8 | 33 / 1 / 44; 8 | 33 / 1 / 44; 8 |
| recent_video | 10 / 2 / 17; 1 | 10 / 2 / 17; 1 | 10 / 2 / 17; 1 |
| scale_video | 19 / 0 / 11; 0 | 19 / 0 / 11; 0 | 19 / 0 / 11; 0 |

The eight internal regression photos overlap the 130-photo set and are reported as a separate regression view, not additional independent evidence or additional primary hits.

## Verification and limits

- Six scoring contracts passed before inference.
- 202 unique images × three fixed checkpoints = 606 full CPU inference records. Duplicate image bytes reused only within the same model identity.
- All original input hashes were preserved. Complete model-state fingerprints were unchanged by inference for all three models.
- PyTorch 2.8.0 CPU, RF-DETR 1.11.2, FP32/math attention, two CPU threads, 512×512 normalized RGB; confidence 0.35, NMS IoU 0.45, match IoU 0.5, top 300 query/class pairs, maximum 100 detections.
- No optimizer updates, new GPU job, checkpoint or threshold reselection, model export, or application adoption.
- Small purposive, assistant-reviewed evidence without independent human recheck. No representative overall accuracy, statistical significance, tracking accuracy, full-vocabulary AP, or source/pretraining independence claim.
- The reserved photos and frames are now consumed evidence. Keep them fixed as regression references; do not call them fresh in future cycles.

Selected checkpoint SHA-256: `c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3`.

Evaluation lock SHA-256: `362e49cb9001e9a06795c59aafc7df0d6a26700ddaf8f592ef7431251fdcfa10`.

Detailed per-class movements are in class-differences.json; changed-frame evidence and source paths are in frame-differences.json.

## Next step

Prepare the separate export, numerical parity, and native runtime performance checks for this exact frozen checkpoint; passing held-out evidence does not by itself approve app adoption.
