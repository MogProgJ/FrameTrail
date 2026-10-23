# Photo-level loss study: fitting task solved; held-scene clean gain still fails

22 October 2026. The user separately authorized this eight-fit objective study. All eight fits/1280 updates completed; timed load/fit/integrity work10.406seconds, below1800seconds. No extra fits, GPU jobs, image inference, validation/TEST caches, detector retraining, model saves, exports or app changes.

## Practical result

The nonlinear probe fits every selected fitting positive query above0.5 and every fitting absent-photo query below0.5 in all four folds. Its highest fitting-negative probabilities are0.0278–0.0416. The capacity and objective are therefore sufficient to fit this particular query task. This does not establish full-image detector fit or sufficient data/representation generalization.

On held TRAIN folds the nonlinear probe still alarms on15/77 absent photos at the fixed0.5 probe cutoff while recovering48/71 known positive queries. The previous full-query BCE probe recovered51/71 with20/77 alarmed photos at0.5: fewer alarms now come with fewer hits. No clean paired support is established.

The frozen fitting-only zero-alarm thresholds fall to roughly0.03 because fitting negatives are suppressed. Applying those locked thresholds to held photos recovers63/71 positive queries but alarms on29/77 absent photos. These are uncalibrated binary-probe scores, not app detector thresholds. Do not deploy or reinterpret them as detector accuracy.

## All held TRAIN diagnostic results

| Objective / probe | Mean fold query AP | Hits at0.5 /71 | Absent photos alarmed at0.5 /77 | Hits at fitting-zero-alarm cutoff /71 | Absent photos alarmed there /77 |
| --- | --- | --- | --- | --- | --- |
| Query-average BCE / linear | 0.4991 | 68 | 77 | 1 | 2 |
| Query-average BCE / mlp32 | 0.6908 | 51 | 20 | 22 | 5 |
| Photo-max / linear | 0.7047 | 70 | 44 | 38 | 8 |
| Photo-max / mlp32 | 0.7160 | 48 | 15 | 63 | 29 |

## Frozen decision and audits

Neither architecture has nondecreasing held hits with nonincreasing absent-photo alarms in all four paired folds against its frozen BCE control. `objective_clean_support_methods=[]`. Query AP is descriptive for this objective comparison; it was not substituted for the count criterion after observing outcomes. No architecture or candidate was selected.

Independent audits recomputed query AP/counts, calibration thresholds, recorded scene/identity separation, full query inclusion, positive weights, negative photo mass, final active-max queries, identical source folds/normalization, BCE references and source/cache hashes. All eight records and traces passed. Source model checkpoint, roles, annotations and scientific gates remain unchanged.

## What this changes

The current evidence no longer supports missing negative-query coverage or inability to fit TRAIN as the sole explanation. It shows a transfer/generalization problem under the fixed TRAIN folds. It does not distinguish limited scene/semantic supervision from frozen feature limitations, and does not prove annotation correctness or a unique causal explanation. Old cross-author scene exhaustiveness is not established. Selected positive queries condition on baseline geometry, other classes/NMS are absent, and these are reused development folds.

The completed detector experiment7870268 still has no qualifying checkpoint, TESTphotos0 and production_adoption=false. Both prior eight-fit studies remain preserved. This third authorized study brings the total to24 diagnostic fits/3840 probe updates across three separately approved scopes, with no deployment models saved.

## Next project step

Stop automatic classifier/query/loss grids as declared. Before choosing more data versus broader feature adaptation, obtain an independent product/domain review of the six-example TRAIN boundary packet. The distinction between business identity signs, information boards and actual advertising panels governs the next supervision plan; it must not be changed merely to improve these scores. No new annotation release or fit has been made.

The review packet supplies original paths/hashes and current scopes, without predictions. It is illustrative, unblinded to existing labels and not representative. Existing frozen labels/results cannot be retroactively changed. After this human input, prepare one bounded data/representation strategy rather than another automatic fit.

Evidence: REPORT.json, INDEPENDENT_AUDIT.json, OBJECTIVE_TRACE_AUDIT.json, PLAN.json, AUTHORIZATION.json, BOUNDARY_REVIEW_PACKET.md and all per-fit traces.
