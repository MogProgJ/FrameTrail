# Training signal check after job 7780632

The classification signal is present. This read-only CPU check used the **12 previously frozen training photos** at steps 0 and 600: 24 model/criterion/backward checks and **zero optimizer updates**. It found no disconnected new-class gradient or violation of the scoped masks in these samples. All parameter/buffer fingerprints and source-file hashes are unchanged.

## Matched positive targets

| Class | Matched targets in two positive photos | Median matched confidence, step 0 → 600 | Median IoU-aware soft target at step 600 | Matched logits whose gradient would raise confidence at step 600 |
|---|---:|---:|---:|---:|
| Cat | 4 | 89.1% → 85.8% | 90.3% | 4 / 4 |
| Dog | 2 | 95.8% → 96.8% | 95.5% | 0 / 2 |
| Billboard | 4 | 0.7% → 2.5% | 33.7% | 4 / 4 |
| Washing machine | 2 | 2.1% → 31.6% | 68.9% | 2 / 2 |

All **4 sampled billboard matches** and **2 sampled washing-machine matches** still have an upward classification signal at step 600. Their mean full classifier-row weight-gradient norms on positive photos are about 18.0 and 24.8 respectively; neither is zero. This is evidence of remaining optimization pressure in these samples, not a forecast of validation improvement. Per-logit descent does not guarantee a shared classifier-row update improves every other query.

The IoU-aware soft target depends on both current confidence and matched-box overlap. The sampled billboard median soft target rises from 24.2% to 33.7%; washing-machine soft target rises from 35.3% to 68.9%. A soft target below 35% at one instant is not a fixed ceiling: it is recomputed as confidence changes. The matched washing-machine IoU changes slightly because Hungarian assignment selects different queries; the box weights did not change.

## Scope, suppression and loss accounting

- Explicit-negative samples produce gradients that suppress the corresponding class. Unknown/unreviewed logits have zero direct gradient, and unmatched logits in positive-only scopes have zero direct gradient.
- All inactive classifier rows have exactly zero masked parameter gradient. No feature, encoder or box parameter receives a gradient. Only the previously approved four final classifier rows were enabled for inspection.
- Gradients from final and auxiliary decoder classification losses reconstruct the actual head gradient. The encoder classification and all box losses are constant with respect to the trainable head.
- On this deliberately small diagnostic set, those frozen loss components account for about **45.2%** of total weighted loss at step 0 and **46.6%** at step 600. Therefore a modest change in the total loss is not a direct measure of how much the new classifier learned.
- Normalization is by the total number of reviewed targets in the photo, clamped to at least one, including targets whose classifier rows are frozen. That can dilute active-class contributions in crowded images; this check does not establish that normalization is a bug or justify replacing it.

The completed sampler already showed 217 billboard-positive and 226 washing-machine-positive photo presentations, drawn from 20 and 21 distinct training photos. All those positives were sampled. They were not omitted, but mixed-class sampling gave each new class less exposure than a class-balanced continuation would.

## Decision supported by the evidence

Together with the earlier validation probe—all 24 new-class targets have a distinct sufficiently overlapping decoder query—this supports testing **more focused classifier optimization before unfreezing features or box heads**. It does not establish the optimal learning rate or enough training duration. A small training-only check cannot demonstrate generalization.

`PROPOSAL.md` and `proposed-protocol.json` specify one bounded two-row continuation: unchanged 0.0001 learning rate, balanced new-class exposure, maximum 2,000 updates, early stop if no eligible gain by 1,000, one A100, maximum 30 active minutes / 45 allocation minutes. Everything except the two new final classifier rows stays frozen. The same validation retention guards and untouched held-out gate apply.

This next GPU run is **not approved or submitted**. Existing approval covered the completed one-off 600-update trial. No training runner, remote action, export or app adoption was created by this diagnostic.

## Evidence and limits

`DIAGNOSTIC.json` and the 24 per-photo records contain each loss component, every active matched target's query/IoU/confidence/soft target/logit gradient, per-row and per-stage gradient norms, and whole-model before/after fingerprints. `INPUT_INTEGRITY.json` pins the original inputs. `SUMMARY.json` contains these aggregates. `proposed-sampling-plan.json` is an unexecuted schedule, not a record of training.

The sample contains only two positive photos per class and the fixed selected explicit negatives, with no independent annotation recheck. No validation or held-out photo was loaded for this training-signal check, no optimizer was instantiated, and no model weights were written. The proposal references the prior validation conclusion but does not run a new validation experiment. The app, annotation scopes, vocabulary, cohorts and previous packages remain unchanged.
