# Distinct next hypothesis: photo-level worst-negative loss

Prepared only. No fit, model, upload or job. Both approved eight-fit diagnostic scopes are complete; their declared automatic-fit stop rules remain in force.

Why this is the next discriminating question: full supervision of all300 fitting-negative queries did not remove all fitting-photo alarms. The nonlinear probe has low mean loss and better ranking, yet no consistent clean operating point. The current query-average loss and the product’s photo-level no-alarm requirement are different objectives. This motivates testing an objective change; it does not prove causality or justify longer training.

Concrete proposed study: reuse the same four recorded scene/identity folds,71 covered positive queries and77 absent photos, frozen baseline features, exact locked parent normalizations, linear and32-unit nonlinear probes, seed17, AdamW lr0.003/wd0.0001 and160updates. Eight new CPU fits total. Reuse the already-completed300-query BCE fits as controls; do not refit those controls.

Single loss change: each positive photo contributes the mean softplus of its negative positive-query logits; each absent photo contributes softplus of its maximum logit across all300 queries. Average each class over photos and give positive/absent classes equal0.5mass. No unmatched partial-positive query becomes negative, no unknown class becomes background, no tuneable penalty coefficient or parameter grid. Do not modify detector confidence thresholds or labels.

Retain fixed0.5 readouts and the same fitting-fold-only zero-alarm threshold, complete fitting/held query traces, weighting and numerical checks. Predeclare clean paired held-fold support before any fit; low loss or training fit cannot promote a model. These are reused TRAIN development folds, not fresh validation/test evidence. No deployable probe/model saved.

Bounds: eight fits/1280updates, two CPU threads,1800s total timed active cap, no retries/replacements/extensions. Zero validation/TEST cache reads, image inference, GPU jobs, detector changes or app adoption. All current scientific/model/data/export gates stay intact. If this also lacks consistent clean support, stop automatic loss/capacity probing and surface a broader representation/supervision strategy decision rather than starting another grid.

Scope decision needed: run this distinct objective study, or stop further RF feature-probe fits and reassess the broader model strategy. This proposal is separate from the two completed user-authorized eight-fit scopes.

Next step: resolve this photo-level loss study scope, because complete negative-query coverage leaves a specific objective-versus-criterion mismatch to test before another GPU run.
