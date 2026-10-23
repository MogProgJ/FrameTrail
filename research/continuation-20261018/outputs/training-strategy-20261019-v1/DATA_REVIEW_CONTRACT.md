# Future release readiness screen

This small offline tool checks the **fresh additions**, separately from historical TRAIN replay and the authoritative full release. It does not adjudicate licenses, content or perceptual similarity. The linked review receipts must represent actual reviews; a passing screen is permission to prepare the package, not evidence of model accuracy or an automatic cluster launch.

`CURRENT_READINESS_INPUT.json` deliberately has no released additions. The latest collection is inaccessible/unconfirmed; the 13 unused old-intake photos are only TRAIN review candidates and cannot count toward fresh addition/evaluation minima. Running the tool now must exit 2 and report shortfalls. Never change a pending flag to make it pass.

Run from PowerShell:

```powershell
& "C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-cpu\Scripts\python.exe" -B -X utf8 "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\training-strategy-20261019-v1\check_data_readiness.py" "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\training-strategy-20261019-v1\CURRENT_READINESS_INPUT.json" --output "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\training-strategy-20261019-v1\CURRENT_READINESS.json"
```

Input schema is `frametrail-billboard-readiness-v1`, taxonomy ID `nextdata7769109-taxonomy-v1`. Pin the existing release and complete prior-intake exclusions using `protected_release_ref` and `prior_intakes_ref`. Each reference is an absolute `path` and `sha256`. Do not substitute a smaller exclusions list. `EXPERIMENT_DESIGN.json` is the single source of pilot counts and diversity limits.

Each record has `image_id`, `split` (`fresh_train`, `fresh_validation` or `fresh_test`), `image_ref` and `review_ref`. The hashed JSON review contains:

| Field | Required meaning |
| --- | --- |
| `image_id`, `image_sha256` | Match the exact reviewed image bytes |
| `identity_group` | Resolved linked author identity; unknown values do not qualify |
| `scene_group` | Resolved scene/session group, including alternate views |
| `source_evidence_ref` | Hashed photo-specific source/license evidence, retained for source review |
| `rights_status` | `cleared-for-private-research` only after actual source/rights review |
| `model_predictions_seen` | Must be false for fresh validation/test, whose labels/splits are frozen before predictions |
| `duplicate_and_scene_review` | `complete: true`, pinned `compared_against_prior_sha256`, and `scene_session_overlap_with_protected: false`, only after SHA/perceptual/alias/scene checks against all previous intakes and known references |
| `other_unknown_classes_remain_unknown` | True; billboard completeness does not create negatives for unreviewed categories |
| `billboard_scope` | `billboard-complete-positive` or `billboard-whole-photo-absent`; no unknown, ROI-only or ambiguous holds |
| `normalized_xyxy` | Exhaustively reviewed in-scope billboard boxes in [0,1]; a nonempty list for complete positives, empty for explicit absence |
| `confuser_family` | For absent TRAIN controls: shop-business-lettering, traffic-information-signs, indoor-frames-screens-boards, or household-laundry |

Before producing these receipts, use the frozen strict category definition from `STRATEGY.md`. Positive scene context alone does not establish exhaustive boxes. Publisher traffic-sign or monitor labels do not establish billboard absence. Preserve ambiguity and incompleteness rather than inventing negative examples.

The tool rejects known reused bytes/IDs, prior held identities, cross-role scene/identity groups, stale evidence/image hashes, missing review scopes, invalid boxes, scene concentration and count/family shortfalls. The complete prior-intake list protects consumed reference bytes from counting as fresh additions. Old unused photos may later be approved separately for TRAIN supplementation, but never converted into fresh validation/test evidence. The checker does not load image pixels or model predictions; decoder, source, semantic and authoritative full-release checks remain mandatory.

Fifteen synthetic contracts exercise valid metadata and the failure paths. Their byte fixtures are not real images and establish no rights or semantic truth. The tests use only the standard library and temporary files within this output folder; nothing is added to the app runtime.

Next step: fill this contract from genuinely reviewed returned data, because passing a metadata screen without the underlying reviews would defeat the experiment.
