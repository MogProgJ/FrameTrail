# Separate full-negative-query coverage control: proposed, not run

The completed authorized scope was eight fits total. This control would add eight, so it requires a separate scope decision. It is not a retry, replacement or extra update of a completed fit. No fit, upload or job has been started for this proposal.

Question: does supervising every fitting absent-photo query reduce the residual alarms, or does the problem persist with complete query coverage?

Exact proposed matrix: the same four frozen scene/identity folds crossed with the same linear and32-unit nonlinear probes,160 updates per fit,1280 updates total. Use the same pinned initial TRAIN features, positive query assignments, seed17, AdamW lr0.003/wd0.0001, fitting-only normalization, equal class/photo mass, fixed0.5 metrics and fitting-fold zero-alarm threshold. Reuse PLAN_V2/FOLDS_V2 and all existing input hashes. No additional model/optimizer/threshold sweep, selection or deployment.

Single intended treatment: replace the32 evenly spaced non-hard negative samples with all268 non-hard queries. Retain the32 baseline-hard queries. Within each absent photo preserve half of its mass for the32 hard queries and half for the remaining268, matching the original hard-versus-other weighting. This replaces the sampled estimate of the other-query term with complete coverage while preserving class/photo mass and hard-negative emphasis. Document that equivalence and validate weights before fitting.

Save full fitting-negative query scores and query indices, per-photo alarms and the largest violating queries. This instrumentation must distinguish residual fitting errors from omitted-query errors; save prediction traces only, no fitted model files. Audit all metrics and fitting-only threshold selection independently.

Resources: sequential CPU only, two threads, total timed active cap1800seconds, no GPUs/cluster jobs. Eight fits maximum, no retries/replacements/budget extensions. No validation or TEST images/caches, no new photo inference, no data/annotation edits, no source-checkpoint or app changes. Existing detector qualification, both baselines, cap530 and locked-winner TEST rules remain intact; this diagnostic cannot promote a model.

Predeclared interpretation: compare paired fold metrics and fitting-photo alarms with the completed64-query study. A lower sampled/full loss is insufficient; seek consistent held-fold recovery without extra absent-photo alarms. No threshold tuning on held-fold scores. These are reused TRAIN development folds, not fresh validation/test evidence. If complete coverage still fails, preserve that result and stop automatic query-sampling/capacity fits; prepare a distinct supervision/loss/representation study before new training.

Next step: choose whether to run this separate eight-fit coverage control, because it directly tests the remaining query-coverage uncertainty within a small fixed CPU budget.
