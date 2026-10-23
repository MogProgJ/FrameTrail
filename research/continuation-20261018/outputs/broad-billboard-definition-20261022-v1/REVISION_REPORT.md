# Billboard definition revision: first image-review pass complete

Business/restaurant identity boards and promotional advertising boards both count, following the user's clarification: "they should both be considered. they are both at the end, billboards". The broader working definition is frozen in TASK_DEFINITION.json. Venue/institution/service identity is a recorded implementation interpretation; uncertain small cards, nonplanar signs, mixed operational displays and dense scenes remain on hold.

All 323 fixed original photos have now been viewed: 124 fresh-role photos, 64 older TRAIN replay photos and 135 older validation photos. This is an assistant review, not independent human annotation. There is no new model fitting, image inference, TEST prediction use, cluster job or app/model change.

The versioned draft adds 41 proposed boxes to the 204 previously scoped photos. It identifies 20 previously absent photos with in-scope boards (19 fresh, one older laundromat replay). Some earlier negative supervision therefore conflicts with the user's intended task. The old experiment results remain frozen narrow-task history; this does not qualify an old model or prove that all remaining errors come from labels.

| Fresh role | Complete positive photos | Partial positive photos | Whole-photo absent | Unknown/hold | Absent-photo shortfall |
|---|---:|---:|---:|---:|---:|
| TRAIN | 34 | 6 | 19 | 1 | 11 |
| Validation | 16 | 1 | 14 | 1 | 6 |
| TEST | 13 | 3 | 16 | 0 | 4 |

These are draft counts, not admitted release counts. The original 30/30 TRAIN and 12/20 validation/TEST positive/absent minima are unchanged. The original minimum is five TRAIN absent photos per confuser family: the current draft lacks five shop/business-lettering negatives and one traffic/information negative. Do not refill shop negatives with physical business boards that now belong to the positive class. Bare facade lettering and other genuinely out-of-scope street objects are candidate confusers, subject to review. Scene, identity, rights, concentration and role checks remain mandatory.

The 119 previously unknown validation photos received a first visual pass, and 32 have display or boundary follow-ups. All 119 remain unknown in this draft: they do not become negative supervision or cleared scoring truth by default. This preserves the meaning of the old unknown-count guard while a separate complete truth overlay is prepared. Crowded old positives remain partial where boxes are incomplete.

Overlay QA also found an inherited class133 box around the 7 Av street-name plate in photo 88ced829147507c7. That target conflicts with the explicit traffic/wayfinding exclusion. It is marked ineligible in the new draft and recorded separately; the old source label and all old results remain preserved. Inherited boxes are provenance, not a guarantee of valid new truth.

All 323 image hashes were rechecked, and the original fresh-release manifest remains b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09. Structural checks pass for role retention, exact inherited boxes, bounded new boxes and no automatic unknown-to-negative conversion. The draft is explicitly not approved for training.

The complete unused local inventory contains 223 source-eligible visual-queue candidates with original prospective roles: 175 billboard-anchor records and 48 other-anchor records (33 TRAIN, 11 validation, four TEST). No current exact-hash or cross-role resolved-owner conflicts were found in that metadata inventory. This is not rights/content/scene clearance, and it does not guarantee enough suitable negatives. Enumerate and review candidates without model-outcome filtering before considering collection.

Before any expanded-task baseline or fit: finish complete target/absence QA, resolve the recorded target conflict, fill role/family shortfalls with prospectively assigned data, revalidate source/rights/scene evidence, and freeze an explicit guard-compatible comparison. Retain both baseline models, other-class invariance, legacy receipts and unknown cap 530. Any semantic conflict with a legacy class133 retention gate must be documented and resolved, never silently waived. Validation remains development evidence already used under the narrow task; TEST remains prediction-unconsumed and cannot select a model. No further old-scope classifier/query/loss grid is authorized by this data revision.

Next step: review the unused local candidates for the missing 11 TRAIN, six validation and four TEST absent photos, including five valid shop-lettering confusers, because the broader task now has a concrete data-coverage gap before another training comparison.
