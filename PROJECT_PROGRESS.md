# FrameTrail progress

Updated 24 October 2026. This is the current entry point; dated reports in the research archive are immutable historical evidence.

## Application

The main build tree now contains the latest desktop source from the verified 19 October continuation: one window with Preview, Analysis, Smooth Playback, Camera and Quick Guide. Navigation retains section state; guide search explains category support and can select a model. The latest package reported a 47.21% smaller core distribution by moving optional models alongside it; this is not a total-storage or inference-speed claim. See the [desktop report](research/continuation-20261018/outputs/native-lean-guide-20261019-v1/REPORT.md) and [source consolidation receipt](docs/SOURCE_CONSOLIDATION_20261024.json).

YOLOX-S remains the default. RF job 7805570 step 100 is an explicit experimental preview. The ONNX numerical hold remains open; `production_adoption=false`. No model has been promoted by this sync.

## Training and findings

The exact four-trial selector batch 7870268 finished and was evaluated once. No checkpoint qualified; `winner=null` and TEST predictions remain zero. Under the frozen narrow billboard labels, final M0 seeds 17/29 scored 11 TP / 8 FP and 10 TP / 8 FP; M1 scored 12 TP / 8 FP and 13 TP / 7 FP on 32 fresh validation photos. Both methods exceeded the legacy unknown-query cap of 530; unknown detections are not automatically false positives. See the [postrun report](research/continuation-20261018/outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md).

Three separately authorized CPU studies completed eight fits each (24 fits, 3,840 diagnostic updates total), using only cached TRAIN features and fixed scene/identity folds. No saved or deployed model resulted. Full-query supervision disproved omitted negative queries as the sole explanation. The photo-maximum loss MLP fit its fitting queries cleanly but still alarmed on 15/77 held-fold absent photos at 0.5, with 48/71 covered positive queries hit. None demonstrated clean support across all folds. These reused TRAIN diagnostics are not independent model qualification. See the [photo-level study](research/continuation-20261018/outputs/train-photo-max-loss-7870268-20261022-v1/STUDY_REPORT.md).

## Accepted task and data revision

The user explicitly confirmed that restaurant/business identity boards and promotional boards both count as billboards. Earlier labels and completed metrics stay frozen. Some earlier negative supervision conflicts with the intended expanded task, so those old results cannot qualify a model under the new definition.

The first original-image review covered 323 photos. The separate draft identifies 20 previously absent photos containing in-scope boards (19 fresh, one old TRAIN). All 119 previously unknown validation photos retain unknown status. The draft is assistant-reviewed, not independent human gold, and is not approved for training. One inherited target around a 7 Av street-name sign is explicitly held and ineligible. See the [revision report](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/REVISION_REPORT.md) and [task definition](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/TASK_DEFINITION.json).

The corrected fresh draft lacks 11 TRAIN, 6 validation and 4 TEST truly absent photos. TRAIN also needs five genuine shop confusers and one traffic confuser to meet the existing family minima. An inventory enumerates 223 unused local candidates with fixed prospective roles; none is admitted yet. Complete content, annotation, rights, scene, duplicate and legacy-guard checks before any expanded baseline or fit. Do not silently treat business boards as negative or unknown photos as background.

## What GitHub contains

The current application and tooling source, earlier source snapshots, research scripts, experiment plans, authorizations, reports, metrics, annotation drafts, provenance records and handoffs are archived in [research/](research/README.md). The source manifest records original byte hashes. Raw media, model/checkpoint files, SDKs, build products, cached feature tensors and authentication/runtime files remain local; an inventory documents exclusions. This repository is a code and evidence archive, not a full binary backup or a data/model release.

Next step: qualify unused local photos to close the 11/6/4 absent-photo gaps, because the expanded billboard definition needs trustworthy coverage before another training comparison.
