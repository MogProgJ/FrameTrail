# Trial 7780632: completed, no improved checkpoint

The retrieved run completed 600 updates, but every validation checkpoint tied the starting model on the frozen selection ranking. The correct selected checkpoint is **step 0**. There is no trained candidate to export or adopt from this run.

## Validation result

All seven checkpoints have 22 complete true positives, 4 complete false positives, 36 complete misses, and 97 hits / 232 known partial targets. Complete F1 is 0.5238095; complete recall is 22/58 (37.93%). These are scoped development results across reviewed classes, not application accuracy or full-vocabulary mAP.

For the four trainable classes, the following counts are unchanged from step 0 to step 600:

| Class | Complete hits / targets | Partial hits / known targets | Complete false positives |
|---|---:|---:|---:|
| Cat | 6 / 6 | 14 / 14 | 0 |
| Dog | 4 / 7 | 6 / 7 | 0 |
| Billboard | 0 / 0 | 0 / 11 | 0 |
| Washing Machine | 0 / 0 | 0 / 13 | 0 |

Billboard and washing-machine rows have **zero known-target hits**. Their targets are partially annotated; zero complete targets or false positives does not establish perfect precision or absence of false positives. Cat's small reviewed subset has no remaining known misses; that is not a general accuracy claim.

| Step | Complete TP | FP | FN | Partial hits | Partial misses | Unscored predictions | Eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 22 | 4 | 36 | 97 | 135 | 525 | yes |
| 100 | 22 | 4 | 36 | 97 | 135 | 524 | yes |
| 200 | 22 | 4 | 36 | 97 | 135 | 524 | yes |
| 300 | 22 | 4 | 36 | 97 | 135 | 524 | yes |
| 400 | 22 | 4 | 36 | 97 | 135 | 524 | yes |
| 500 | 22 | 4 | 36 | 97 | 135 | 524 | yes |
| 600 | 22 | 4 | 36 | 97 | 135 | 525 | yes |

The selection ranking is `(119 reviewed positive hits, 0.5238095 complete F1)` at every checkpoint. Exact ties retain the earlier checkpoint under the frozen protocol. Unknown predictions are unscored, not false positives.

## What was independently verified

- Archive SHA-256 matches the pinned retrieval value: `ae4fcd247566cc0a9c2abe81f8e25a61626e1987d1f950d8af5ddecc2db8a3ff`.
- Candidate, protocol and approval identities match the preflight receipt.
- All 600 numbered update records match the reproduced seeded schedule: 2,400 presentations from 158 distinct training photos (111 positive-pool photos and 47 negative-pool photos). No validation or test IDs appear in the schedule.
- All seven saved prediction sets reproduce their aggregate and all 72 per-class metric records using the frozen scorer. Eligibility and selection were recomputed.
- `best.pt` is byte-identical to `checkpoints/step-0000.pt`, with hash `3a9adf74b11b851fba7393cc41b12b538a7aa1576b0a4e179468cc36c2279389`.
- CPU tensor comparisons of step 0 and step 600 show changes only in `class_embed.weight` and `class_embed.bias`, and only in rows 15, 16, 133 and 593. All other parameters, buffers and classifier rows are exactly equal.
- The four trainable rows changed, so this was not a case of zero weight updates. Nonzero recorded gradients and finite losses agree with that finding. Mean loss across the first 100 updates was 9.1862; across the last 100 it was 8.8366. This small change did not improve the frozen validation ranking.

There were 38 cat predictions above threshold at step 0 versus 37 at step 600, 12 dog predictions at both, no billboard predictions at either, and 0 versus 1 washing-machine predictions. The single washing-machine prediction did not match a reviewed target. Prediction counts alone are not accuracy metrics.

## Evaluation and application disposition

The 130 held-out photographs and 24 reserved frames from six sequences were not evaluated in this audit. Their gate remains **deferred, not passed**. Step 0 is the starting reference, and the predeclared adoption gate requires a useful strict gain. This trial has already failed to produce a development candidate with that gain; using reserved data cannot turn the selected step-0 checkpoint into an improved trained model.

No new training, model download, inference, export, application weight replacement or GUI change was performed. The separate GUI Studio package remains available with its previously packaged models; job 7780632 has not been integrated.

## Concrete follow-up

Run a validation-only confidence and localization probe on the **28 known misses** listed in `validation-misses.json`: 4 dog, 11 billboard and 13 washing-machine targets. Prioritize the 24 new-class misses. Compare step 0 and step 600 before thresholding: strongest target-class logits, same-class query overlap, best query-box overlap regardless of label, and the encoder proposal's overlap/category. Keep the frozen scorer and threshold unchanged; store these diagnostics separately.

This separates low class confidence from missing localization/proposals before proposing a broader training scope. Frozen random new-class encoder rows and frozen features/boxes are possible constraints from the implementation, **not a demonstrated cause**. The saved thresholded predictions cannot establish that cause. Do not rerun training, lower production thresholds, or consume held-out data as part of this diagnostic.

## Limits and reproducibility

The annotations were assistant-reviewed, with no independent human recheck. Partial classes support known-positive recall only; unknown classes do not establish negatives. The audit reads existing artifacts and loads tensor checkpoints with `weights_only=True` on CPU. `audit_trial.py`, `finish_report.py`, `AUDIT.json`, the two diagnostic worklists and `INPUT_INTEGRITY.json` preserve the procedure and evidence. Running the audit scripts writes only their own output folder.
