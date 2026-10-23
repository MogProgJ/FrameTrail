# Proposed separate TRAIN-only discrimination study

Status: prepared for a scope decision; no new fit, upload, job or model produced.

Why: both frozen methods failed all qualification rules despite fresh validation gains. The final two-head states still alarm on12–13 fresh TRAIN absent objects and miss8–11 fresh TRAIN targets with38/38 and37/38 usable geometry. The inspected mistakes include obvious traffic signs, whiteboards and framed pictures, so broadening billboard labels would not resolve the demonstrated confusion. Do not tune thresholds against the completed validation outcomes.

Recommended scope: a diagnostic comparison using only the124 existing TRAIN photos and pinned cached features. Four deterministic folds must keep each scene, linked author/identity and known merged scene entirely in one fold. Compare a linear query classifier with the existing32-unit nonlinear probe,160 fixed updates per fit, two CPU threads, eight fits total, no parameter sweep or deployed checkpoint. Exact balancing, optimizer settings, training-only normalization, cache identities, query assignments and fold feasibility must be frozen and checked before any fit. Reuse the prior capacity-diagnostic settings where compatible; record any necessary change. Known positives only; unmatched queries on partial old positives remain unknown. Negative queries may come only from reviewed complete/absent billboard scope.

This proposal is not runnable or sealed. Scene/identity group counts and feasible fold assignments must be verified; do not silently substitute random query folds. Cap total diagnostic CPU active time at1800seconds; preserve partial evidence without extending/retrying. No GPU or cluster cost. Do not use old/fresh validation or TEST images/features for fitting, early stopping, model choice or calibration. The existing fresh TEST remains untouched for a future single qualified locked winner.

Readouts: per-fold query ranking and a fixed training-fold operating criterion, held-fold positive recovery and absent-photo alarm counts, and variation across folds. These are TRAIN diagnostic results, not detector validation accuracy. No model release or architecture adoption follows automatically. A nonlinear probe must show a consistent improvement at a comparable false-alarm criterion before a separate deployment/adapter experiment is justified; otherwise study supervision/loss/representation rather than adding capacity by assumption.

Choice needed: proceed with this new TRAIN-only study, or close the RF fine-tuning line and redirect the next model work. This is a new scientific fit scope after the frozen four-trial stop rule, not a retry or extension of7870268. No scope decision has been inferred from the failed results.

Next step: resolve this separate TRAIN-only study scope, because the current experiment has no eligible model and further fits would exceed its frozen design.
