# TRAIN-only discrimination study: eight fits complete

22 October 2026. The user explicitly chose “Run the separate TRAIN-only discrimination study (recommended)” after the completed detector experiment had no qualifying model. AUTHORIZATION.json preserves this separate scope; it supersedes the earlier pending-scope text for this study only. No detector retraining or cluster job occurred.

The small nonlinear probe improved mean query ranking but did not provide a consistent clean operating advantage. It failed the rule frozen before fitting. No architecture or model was selected, retained, exported or installed.

## Design and execution

-124 existing TRAIN photos inspected through pinned cached features only.122 participate:45 positive photos with71 one-to-one geometry-covered positive queries, plus77 whole-photo absent photos. Two old positives have no covered query and are explicitly excluded, not relabeled negative.
-Four folds keep every recorded identity/scene component together, including transitive old Times Square links. Old cross-author scene exhaustiveness is not claimed. All four held folds contain fresh positives.
-The initial metadata-only preparation put no fresh positive in fold0. That preparation and its hashes remain preserved. PLAN_V2.json/FOLDS_V2.json repaired balance before any fit or fit prediction. These are the actual frozen fit inputs.
-Linear256→1 and nonlinear256→32→1 probes,160 fixed updates each, eight fits/1280 diagnostic updates total, two CPU threads, AdamW lr0.003/wd0.0001, initialization17. Same prior-probe settings; fitting-fold-only normalization and equal class/photo mass.
-Only32 baseline-hard plus32 evenly spaced other negative queries per fitting absent photo. All300 queries are scored on held absent photos and for fitting-fold calibration. Unmatched positive-photo queries remain excluded, including unknown old partial scopes. No unknown class becomes background.
-Fixed0.5 probe scores retained for comparison. A second threshold is locked separately per fit strictly above the highest score across all300 queries of fitting-fold absent photos, before held-fold scoring. It is never calibrated on held scores and is not an app confidence threshold.
-Timed fitting/load/final integrity phase5.187seconds, well below1800seconds. Runtime startup/preparation are separate. No retries, extensions or extra fits. Source/cache hashes unchanged. No validation/TEST cache reads, new image inference, GPU use or model files.

## Independently recomputed results

| Probe | Mean fold query AP | Held hits at0.5 /71 | Held absent photos alarmed at0.5 /77 | Held hits at TRAIN-zero-alarm criterion /71 | Held absent photos alarmed at that criterion /77 |
| --- | --- | --- | --- | --- | --- |
| Linear | 0.6391 | 68 | 77 | 18 | 4 |
| Nonlinear32 | 0.6849 | 51 | 21 | 22 | 6 |

The nonlinear probe improves query AP in three of four folds but worsens it by0.0400 in fold1. At the fitting-fold zero-alarm criterion, fold2 gains two hits while adding alarms on three more absent photos. Fold3 gains two hits and removes one alarm; folds0/1 have the same operating hit/alarm counts. The predefined all-four-fold non-worsening rule fails. Mean ranking improvement alone does not satisfy it.

At0.5, lower nonlinear alarm counts also come with lower positive recovery. The pooled query/photo results are descriptive TRAIN diagnostics conditioned on frozen box coverage, not detector recall, mAP, app false-alarm rates or independent test accuracy. There is no NMS/other-class competition in these binary probes.

## Remaining uncertainty

The nonlinear sampled training loss is about0.0031–0.0037, but evaluating all300 queries on its own fitting absent photos finds alarms on5–8 photos per fit. Each fit supervised only64/300 queries per absent photo. This makes negative-query coverage a concrete next variable to control. The retained per-photo maxima do not establish whether individual alarms came from sampled or omitted queries; do not claim omission caused the errors. Rare sampled errors, weighting/optimization and generalization may also explain them.

The diagnostic supports neither “a bigger head solves it” nor “frozen features can never work.” The current row-only detector recipe stays closed, and the starting model stays unchanged. Fresh TEST remains unused.

Next step: resolve the separate full-negative-query coverage control described in FULL_QUERY_CONTROL_PROPOSAL.md, because the completed eight-fit scope cannot distinguish incomplete query supervision from discrimination failure across all fitting negatives.
