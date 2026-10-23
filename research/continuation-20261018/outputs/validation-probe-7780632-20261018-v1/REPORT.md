# Why trial 7780632 missed the new classes

This offline CPU probe compared step 0 and step 600 on **15 existing validation photos containing 28 known misses**: 11 billboards, 13 washing machines and 4 dogs. All 30 full-model forwards reproduced the saved KIT decoded outputs within the declared parity checks (same detection count/classes, matched box IoU ≥ .99 and confidence difference ≤ .002).

## Measured result

| Class | Known misses | Targets with a decoder box at IoU ≥ .5 | Median of per-target strongest class confidence, step 0 → 600 | Maximum class confidence at step 600 | Targets covered by all encoder proposals → selected proposals |
|---|---:|---:|---:|---:|---:|
| Billboard | 11 | 11 | 1.65% → 3.96% | 4.22% | 11 → 10 |
| Washing machine | 13 | 13 | 3.06% → 28.98% | 36.90% | 13 → 13 |
| Dog | 4 | 4 | 24.33% → 32.37% | 94.30% | 4 → 4 |

The median uses one strongest query confidence per target; targets in the same photo share that value. These are raw scores before filtering. The confidence cutoff remains .35 (35%); no threshold was tuned. A geometrically covering box ignores its class label and is an oracle diagnostic, not a successful detection.

Of the **24 new-class misses**, **24** already have a decoder box overlapping the target at IoU ≥ .5 but no query with both adequate overlap and class confidence ≥ .35. The other **0** lack any final decoder box at that overlap. There are **1** targets covered by some encoder proposal but absent from the selected 300 proposals, and **0** covered by selected encoder proposals but lost after decoder refinement; these stage comparisons describe coverage and may overlap.

The classifier rows did learn different numbers, but their confidence changes did not yield a usable new-class detection. Crucially, **all 24 new-class targets already have a geometrically usable decoder box**. An additional one-to-one assignment check confirms that distinct queries can cover all 24; this is not merely counting the same query for multiple targets. Localization is not the demonstrated bottleneck on this failure subset. The one encoder-selection coverage loss is recovered by the decoder. There is no measured reason here to unfreeze the box regressor.

On queries that actually overlap the targets sufficiently, median best billboard confidence rises from 0.93% to 3.30%, and washing-machine confidence rises from 2.39% to 22.58%. The highest washing-machine score anywhere reaches 36.90%, but that query does not sufficiently overlap a reviewed washing-machine target. The highest washing-machine score on a covering query is 32.17%, still below 35%.

The final decoder boxes, selected encoder boxes and all encoder boxes were bit-identical between the checkpoints on every probed photo. This verifies the frozen localization scope; unchanged geometry does not mean the existing boxes were unusable.

## What this does and does not establish

The measured limitation for the 24 new-class targets is inadequate correct-class confidence on existing boxes. The data do not establish whether the best remedy is more classifier optimization, different learning rates, better loss balance, additional reviewed data or adaptation of shared features. A wider fine-tuning scope has not been justified by this probe. Scores are not calibrated probabilities of real-world correctness. The 4 dog misses also have a covering decoder box but insufficient confidence on covering queries; this is a separate retention diagnostic, not a claim about all dogs.

The training loss is IoU-aware: its positive classification target depends on the matched box overlap, while box parameters were frozen. This is a source-code observation in the sealed `scoped_rf.py`; poor overlap can constrain the supervision signal. This validation probe did not inspect training-time matches and does not establish that mechanism as the sole cause.

No GPU job, training, threshold change, model export, application update, annotation edit or held-out evaluation occurred. All original input hashes are unchanged. The reserved 130 test photographs and 24 video frames remain unused. The existing app model remains installed separately.

## Best next step

Run a small **training-only classification-loss and gradient diagnostic**, without optimizer updates, on fixed positive and explicit-negative samples for the four approved rows. Inspect per-class exposure, matched box overlaps, IoU-aware soft targets, loss normalization and row-gradient norms at steps 0 and 600. `training-exposure.json` already reconstructs the completed sampler's exposure; `TRAINING_DIAGNOSTIC_PLAN.md` defines the remaining check.

Use that evidence to prepare a bounded next optimization proposal with the same retention guards and untouched held-out gate. Prefer the narrowest scope that addresses the measured classification problem; a new GPU trial needs separate approval. Do not repeat the same run blindly, unfreeze box parameters based on this probe, or lower the app threshold to make validation misses appear solved.

## Evidence

- `index.html`: photo-by-photo overlays and before/after raw scores for all 28 targets.
- `PROBE.json`: full per-target, per-stage diagnostics and CPU/KIT parity checks.
- `SUMMARY.json`: aggregate results and each target's observed limitation.
- `raw/`: compact NumPy outputs for decoder, all encoder proposals and selected proposals at both checkpoints; no model weights.
- `INPUT_INTEGRITY.json`, `VALIDATION_RECEIPT.json`: source identities and checks.
- `probe.py`, `summarize.py`: reproducible offline procedure. Runtime: Torch 2.8.0+cpu, RF-DETR 1.11.2; the completed KIT trial used Torch 2.8.0+cu128. Numerical parity was checked rather than assuming CPU/CUDA identity.

An initial local CPU attempt was interrupted after six photos when the tool session reset; its partial files were preserved in the prior work directory. This deliverable uses a fresh complete run. It contains no remote resubmission or additional training.
