# Job 7805570: retrieval verification repaired and results audited

The existing downloaded archive passed SHA-256 verification. No download, GPU training, or submission was repeated. The original helper and failed extraction remain preserved.

## Why the verifier failed

The approved sampling plan is JSON stored with Windows CRLF line endings and a final newline. The training program loaded that plan and saved the same JSON values using Linux LF line endings without a final newline. The old verifier reconstructed a third serialization (LF plus a final newline) and incorrectly compared its byte checksum with the approved Windows file checksum.

The replacement verifies the exact original reference SHA-256, then compares all returned JSON values and their order with that reference. It also verifies every actual step receipt. All 2,000 approved batches match. Six regression tests cover the formatting case, changed images, changed order, missing updates, a corrupt reference, and archive path traversal. All passed.

## Independently checked result

All 21 saved validation records were rescored from their saved detections against the unchanged 135-photo validation partition. Eligibility against both baselines and checkpoint selection were recomputed. Step 100 remains the selected candidate.

| Class | Starting known targets detected | Step 100 |
|---|---:|---:|
| Cat | 20/20 | 20/20 |
| Dog | 10/14 | 10/14 |
| Billboard | 0/11 | 0/11 |
| Washing machine | 0/13 | 8/13 |

Across the validation set, complete-scope TP/FP/FN remain 22/4/36. Partial known-positive hits increase from 97 to 105. Aggregate unscored predictions increase from 525 to 528, within the approved +5 allowance. Unscored predictions are not measured false positives. The washing-machine targets have partial annotation scope, so this gain does not establish full precision for that class.

Later checkpoints failed retention checks; the final step-2000 checkpoint is not selected. Its extra detections must not replace the eligible step-100 candidate.

CPU tensor comparisons confirm the starting checkpoint was loaded exactly. At step 100 and step 2000, only the final classifier weight and bias tensors changed, and only their two permitted rows changed. All other classifier rows, features, encoder, and box tensors remain identical to the starting model.

The archive checksum is `7212bd624027deb14de2e81166710177b03765067a2ba65f669a60d75f62fdab`.
The selected checkpoint checksum is `c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3`.

## Limits and next step

These are development validation results from assistant-reviewed scoped annotations, not an independently audited accuracy benchmark. No held-out inference, export, or app adoption occurred during this repair/audit. The candidate is not approved for application use.

Next step: evaluate the frozen step-100 checkpoint against the pinned baseline on the reserved held-out photos and video frames with unchanged thresholds, because validation selection alone cannot establish that the gain generalizes.
