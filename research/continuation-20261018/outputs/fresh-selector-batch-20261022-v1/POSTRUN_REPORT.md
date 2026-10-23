# FrameTrail paired comparison: completed, no qualifying model

22 October 2026. The exact existing local follow-up completed successfully on verified array 7870268. All four scientific conditions are complete. Neither method qualifies in either seed. Keep the starting model; production adoption remains false.

The two-head method learned to detect more billboards, but it also labeled other signs and rectangular objects as billboards. This problem appears on TRAIN as well as validation. The evidence supports changing the discrimination study, not extending this recipe or unfreezing box layers.

## Validation at every frozen checkpoint

Each cell is fresh billboard hits / false alarms on 32 validation photos with 14 targets. No thresholds or annotations changed.

| Method / seed | 0 | 100 | 250 | 500 | 1000 | 1500 |
| --- | --- | --- | --- | --- | --- | --- |
| M0 / 17 | 0 / 0 | 0 / 0 | 0 / 0 | 4 / 2 | 9 / 7 | 11 / 8 |
| M0 / 29 | 0 / 0 | 0 / 0 | 0 / 0 | 5 / 2 | 9 / 7 | 10 / 8 |
| M1 / 17 | 0 / 0 | 0 / 0 | 0 / 0 | 3 / 2 | 10 / 7 | 12 / 8 |
| M1 / 29 | 0 / 0 | 0 / 0 | 0 / 0 | 4 / 1 | 11 / 8 | 13 / 7 |

M0 updates only the main billboard classifier row. M1 updates the main and encoder proposal billboard rows. The starting model has zero hits and zero billboard false alarms on this fresh validation set.

Every checkpoint that gained at least three fresh hits added false alarms. Each also added one billboard false alarm on the older reviewed set, failing retention against both baselines. At step1500, old unscored counts are M0 538/538 and M1 542/538, above the original fixed cap530. Unscored predictions are not automatically false positives. No other reviewed class metric triggered the per-class retention failures recorded here.

## Fixed final TRAIN diagnosis

These postrun diagnostics used only the 124 already-approved TRAIN photos, no optimization and no new validation/TEST predictions. They do not reopen checkpoint selection. Fresh positives have complete billboard annotations (38 targets); the 50 old positive targets remain partial-scope recall evidence.

| State | Fresh TRAIN hits /38 | Fresh-positive false alarms | Fresh-absent false alarms | Old-absent false alarms | Fresh geometry coverage /38 | Old geometry coverage /50 |
| --- | --- | --- | --- | --- | --- | --- |
| starting-model | 0 | 0 | 0 | 0 | 36 | 35 |
| M0-17-1500 | 27 | 7 | 12 | 7 | 36 | 35 |
| M0-29-1500 | 27 | 6 | 8 | 7 | 36 | 35 |
| M1-17-1500 | 30 | 4 | 13 | 8 | 38 | 47 |
| M1-29-1500 | 27 | 7 | 12 | 6 | 37 | 47 |

The M1 seeds provide usable boxes for38/38 and37/38 fresh TRAIN targets, yet miss8 and11 at the unchanged operating point and alarm on 13 and 12 fresh absent-photo objects. This is evidence of a discrimination/operating-point problem even on TRAIN; it does not prove whether loss weighting, frozen features or limited classifier capacity is the cause. There is no basis here for claiming box-regressor unfreezing is necessary.

## Error inspection

All three derived error sheets (23 distinct TRAIN photos with a final-state false alarm in at least one condition) were visually inspected. Clear confusions include road restriction/warning signs, a bus-stop board, whiteboard, framed pictures, shop identity signs and business lettering. Positive-photo errors include a transit display beside a real billboard, a subpanel instead of the whole board, and merging/splitting adjacent advertising panels. These are qualitative observations from derived overlays, not a new exhaustive original-image annotation audit.

The recorded category near-target-IoU-below-0.5 means any positive target overlap below0.5; it does not alone establish a localization error. Source labels, scopes, split roles and hashes remain unchanged. No errors were relabeled after seeing predictions. The cohort remains assistant-reviewed private research, not independent human annotation.

## Execution and limits

- M1 combined training plus validation: seed17 1071.375s; seed29 1063.401s, both below1800s.
- All24 saved validation records, per-image count totals/F1, qualification decisions and6000 paired update-log entries were independently audited. This is a record/decision audit; fresh per-box predictions were not independently re-inferred.
- Starting-state identity and inactive/frozen parameters passed the original pipeline and TRAIN diagnosis. Starting checkpoint SHA c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3 remains unchanged.
- No winner lock, fresh-TEST consumption lock, known-regression inference or fresh-TEST inference. TEST photos used0. No export, app changes, production adoption, new cluster jobs, retrieval, resealing, retraining, retries or replacements.
- No access to Carrington Event or other projects. No MiniERP edits. No background process or automation remains after completion.
- Schedule files were sealed after the baseline but before fits, as preserved in EXECUTION_ORDER_NOTE.json; do not describe the implementation as literally fully preregistered.

## Next decision

Close this four-condition experiment under its frozen failure rule. The best next separate study is TRAIN-only billboard-versus-sign discrimination: reuse existing frozen TRAIN features and compare a fixed linear control with a small nonlinear probe in scene/identity-disjoint TRAIN folds before any deployable architecture or GPU proposal. The prior small-data capacity test found no consistent nonlinear advantage, so a fresh-data repeat must be treated as a diagnostic question, not a justified new model already selected.

No further fit is authorized by this result. The focused continuation explicitly prohibited retraining, and the frozen strategy says to stop this recipe when neither method qualifies. A separately agreed study scope is needed before new fits; keep the taxonomy, both baselines, unknown cap, TEST isolation and resource limits intact. See NEXT_STUDY_SCOPE.md for the concrete bounded proposal.

Evidence: retrieval/local-evaluation/{FINAL_REPORT,GLOBAL_SELECTION}.json; postrun-audit-7870268-v1/INDEPENDENT_AUDIT.json; postrun-train-diagnosis-7870268-v1/{PLAN,REPORT}.json and review/REVIEW_QUEUE.json.
