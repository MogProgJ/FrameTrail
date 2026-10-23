# Full-negative-query control: complete; no qualifying clean advantage

22 October 2026. The user separately authorized eight additional CPU fits. Exactly eight fits/1280 diagnostic updates completed in8.672seconds of timed load/fit/integrity work, below1800seconds. No validation/TEST data, new image inference, GPU job, detector retraining, export or model adoption.

The nonlinear probe ranks positive queries better than the linear probe in all four folds under this control. It still adds held absent-photo alarms in two folds at the fitting-fold criterion and fails the frozen clean-gain rule. Compared with its own64-query result, complete coverage provides no consistent clean improvement. Stop automatic query-sampling/capacity fits as declared.

## Controlled treatment

The same122 TRAIN photos,71 covered positive queries, four recorded scene/identity folds, initializations, models and160 updates were retained. Positive supervision is unchanged. All300 fitting-absent queries now enter the loss:32 unchanged baseline-hard queries share half the photo mass;268 other queries share half. Class/photo mass remains fixed.

Before fits, exact parent fitting-fold means/stds were locked to avoid changing preprocessing with query coverage. PLAN_V3.json is authoritative; the earlier preparation/code is preserved. Independent audit verifies every query is included, exact loss weights, identical folds and normalizations, full calibration traces and fitting-only thresholds.

## Held TRAIN-fold results

These are binary query diagnostics on reused TRAIN development folds, not detector or app accuracy. Each threshold is locked strictly above all fitting-fold negative scores before held-fold scoring.

| Study / probe | Mean fold query AP | Hits at0.5 /71 | Absent photos alarmed at0.5 /77 | Hits at fitting-zero-alarm criterion /71 | Absent photos alarmed at that criterion /77 |
| --- | --- | --- | --- | --- | --- |
| 64queries / linear | 0.6391 | 68 | 77 | 18 | 4 |
| 64queries / mlp32 | 0.6849 | 51 | 21 | 22 | 6 |
| 300queries / linear | 0.4991 | 68 | 77 | 1 | 2 |
| 300queries / mlp32 | 0.6908 | 51 | 20 | 22 | 5 |

In the300-query control, nonlinear versus linear gains2/7/9/3 held hits by fold, with absent-photo alarm changes-1/+1/+3/0. This fails the predefined no-extra-alarm requirement in folds1/2. Against the previous nonlinear probe, fitting-zero-alarm hits remain22/71 and alarmed photos fall from6/77 to5/77, but the changes are not consistent across folds. Ranking gains do not establish a clean deployable operating point.

## Fitting errors after complete supervision

| Fold / probe | Fitting absent photos | Fitting absent photos alarmed at0.5 | Supervised negative queries alarmed | Baseline-hard / other alarm queries |
| --- | --- | --- | --- | --- |
| 0 / linear | 58 | 58 | 2319 | 485 / 1834 |
| 0 / mlp32 | 58 | 4 | 4 | 2 / 2 |
| 1 / linear | 57 | 57 | 2239 | 464 / 1775 |
| 1 / mlp32 | 57 | 6 | 9 | 2 / 7 |
| 2 / linear | 58 | 58 | 2397 | 463 / 1934 |
| 2 / mlp32 | 58 | 7 | 7 | 4 / 3 |
| 3 / linear | 58 | 58 | 2566 | 488 / 2078 |
| 3 / mlp32 | 58 | 6 | 6 | 2 / 4 |

The remaining fitting alarms are now known to be on supervised queries. Omitted negative queries therefore cannot fully explain these control errors. This does not prove the optimizer, loss, labels or frozen features are uniquely responsible. Low average query loss alone does not enforce a no-alarm photo criterion; rare high-confidence errors can remain under the fixed recipe.

No new data, taxonomy, annotations, thresholds or detector gates were changed. The probe0.5 thresholds and fitting thresholds are not FrameTrail app confidence settings. Old cross-author scene exhaustiveness is not established; only recorded scene/identity links are enforced. Existing geometry conditioning and prior development history limit the inference.

## Next research decision

The best next hypothesis is a photo-level worst-negative objective that directly addresses each absent photo’s most confident false alarm. That is a distinct loss study, outside both completed eight-fit scopes, and has not been run. A concrete proposal is in NEXT_OBJECTIVE_STUDY_PROPOSAL.md. No further automatic query-sampling/capacity fits are warranted.

Current detector remains the starting checkpoint. The completed detector experiment still has no eligible winner; TEST is untouched; production_adoption=false.

Evidence: REPORT.json, INDEPENDENT_AUDIT.json, FULL_QUERY_TRACE_AUDIT.json, PLAN_V3.json, AUTHORIZATION.json and per-fit score traces.
