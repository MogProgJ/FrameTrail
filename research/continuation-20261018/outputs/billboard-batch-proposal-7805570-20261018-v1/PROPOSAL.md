# One submission: four billboard trials and their regression checks

This draft supersedes the unsubmitted single-trial proposal. **No approval file, upload or new cluster submission exists.** The older proposal and all historical receipts remain preserved.

## Fixed experiment matrix

All four tasks independently start from job 7805570 selected step 100, checkpoint SHA-256 `c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3`.

| Array index | Positive : explicitly absent photos per update | Learning rate | Maximum updates | Maximum presentations |
|---|---|---|---|---|
| 0 | 1 : 1 | 0.0001 | 3,000 | 6,000 |
| 1 | 1 : 3 | 0.0001 | 3,000 | 12,000 |
| 2 | 1 : 1 | 0.0003 | 3,000 | 6,000 |
| 3 | 1 : 3 | 0.0003 | 3,000 | 12,000 |

Task 1 retains the original proposed experiment. The additional tasks compare explicit-negative share and learning rate in a small factorial design. Paired trials share the same positive sequence and negative prefixes; learning-rate pairs consume identical image schedules. Positive exposure and update budgets match across trials. This gives useful comparisons of two unresolved choices in one batch, rather than four sequential approval/authentication cycles. It is not a seed replication or a claim of statistical significance.

There are 20 existing positive training photos and 35 photos with explicit billboard absence. No inferred negatives, new labels, new images, vocabulary changes or threshold changes are introduced. The overall sealed release remains 965 photos: 700 training, 135 development and 130 now-consumed regression photos. Training samples come only from the training partition.

## Exact resource scope

- One Slurm array submission: `--array=0-3%2`, regular `gpu_a100_il` partition.
- Four tasks, each requesting one A100, two CPU cores, 8 GiB host memory and 45 minutes wall time. At most two tasks / two GPUs, four CPU cores and 16 GiB host memory run concurrently.
- Each task caps the training process at 1,800 seconds, then caps automatic known-regression processing at 480 seconds. The 45-minute wall limit includes setup and result archiving.
- Aggregate upper bound: 12,000 optimizer updates, 36,000 training-image presentations, two GPU-hours of capped training-process time, and **three GPU-hours of requested wall allocation**, including all four tasks' overhead and postprocessing. This is a budget ceiling, not a predicted runtime. Queue wait and task placement are scheduler-controlled; concurrency is a ceiling, not a guarantee.
- Stop a trial at update 1,500 if no eligible strict gain has been selected; otherwise at most 3,000 updates. No automatic retries, requeue or replacement jobs. One task failure does not cancel independent tasks.

Only final classifier row **133 (billboard)** can change. Washing machine, cat, dog, every other classifier row, features, encoder, boxes, parameters and buffers remain frozen and checked. Optimizer, math attention, seeds, clipping and validation cadence follow the proven continuation implementation, with only the fixed ratio and learning-rate variants above.

## Automatic work included

1. Verify code/assets/runtime and run a read-only Slurm submission test before the real submission. Record scheduler/account-limit queries when access permits. If the scheduler rejects this array, stop without submitting a fallback job.
2. Run all four independent trials with validation at step zero and every 100 updates. Each reviewed class must retain true positives and known-positive hits without increasing complete-scope false positives, against both the original model and selected step-100 model. The effective aggregate unscored-prediction cap remains 530. Ties retain an earlier checkpoint.
3. Freeze each validation-selected checkpoint hash. A useful new candidate automatically runs inference on the same **202 unique known regression images / six reference sets**, with scoped scoring against original and current baselines. A step-zero outcome reuses pinned current-model scores without duplicate inference. Regression outcomes cannot reselect a checkpoint or variant.
4. Archive each task, including failures, under its explicit `array_id_task_index` identity. Keep best/last model states, update trace, validation predictions, gradient/freeze receipts and regression evidence. Intermediate checkpoint copies stay on KIT rather than being duplicated in downloads.
5. One Check command reports the array; one Retrieve command downloads all four task archives and verifies their exact identities and schedules. A provisional local validation-only comparison applies the predeclared ranking and stable array-index tie break after all four trials have been retrieved and structurally verified. Independent CPU rescoring and tensor-freeze audits remain required local follow-up before accepting a winner; they need no extra cluster job or routine approval. Any failed/partial trial leaves the comparison incomplete for inspection; there is no automatic adoption.

One common sealed input package is uploaded, rather than four copies. The launcher is one user command; SCP and SSH may each request KIT authentication. Credentials must be entered directly in their prompts.

## Why this is the useful batch now

The selected model improved known washing-machine targets from 0/15 to 3/15, but billboard remains 0/19 on known regression photos. The rejected later checkpoint showed billboard learning together with false positives and unscored drift. The training-only diagnostic found positive and suppressive-negative gradients, motivating the ratio/rate comparison. Increasing the grid further would add more development-set selections without a fresh independent test. Backbone/box retraining would be a materially different experiment; one reviewed training photo has two targets with no covering query, which this frozen-box scope cannot repair.

All old references have already been consumed. These are regression checks, not a fresh generalization test, and a four-way validation search increases development-set selection pressure. Further independent frozen evidence is needed before a new generalization claim. No reference labels or scopes are altered.

The strict ONNX numerical-export hold remains separate. This batch does not claim to fix it. Export variants and native GUI/CPU packaging run locally under the standing autonomy instruction after results are audited; they do not need additional GPU jobs or local approval checkpoints.

## Limits and account verification

Slurm arrays support a concurrency cap but each task still counts toward account job limits. Public KIT partition maxima describe cluster resources, not this user's account entitlements. The current exact permitted job/GPU count cannot be established from this unauthenticated desktop. During the approved launch, read-only scheduler/account queries and `sbatch --test-only` run before the single real submission; no account limit is increased or bypassed. Account queries that are unavailable are recorded as unavailable, not interpreted as unlimited.

Sources checked on 18 October 2026: [Slurm job-array support](https://slurm.schedmd.com/job_array.html), [KIT bwUniCluster 3.0 running jobs](https://wiki.bwhpc.de/e/BwUniCluster3.0/Running_Jobs). KIT uses fair-share scheduling, so requesting the theoretical maximum is not the same as obtaining the fastest useful result.

## Prepared validation

Twelve local CPU/structural checks passed, including four schedules, paired comparisons, synthetic row-only updates at both learning rates, pinned starting-runtime checks, consumed-image hashes, archive containment, both supported completion rules and validation-only tie selection. Six local mock-Slurm cases passed: preflight rejection, scheduler-test rejection, repeated normal launch, ambiguous submission response, successful batch entry and training-failure archiving. No real model updates or GPU inference were performed locally for these tests. Five helpers parse under Windows PowerShell 5.1; missing approval stops before packaging or SSH.

Executable draft: `rf-billboard-batch-0a255598-v1`. Protocol SHA-256: `0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd`. PREPARATION_RECEIPT.json and package-files.json pin the final prepared files.

Next step: approve this one four-trial batch, because it compares both plausible calibration choices and collects regression evidence in the same submission while protecting the current gain.
