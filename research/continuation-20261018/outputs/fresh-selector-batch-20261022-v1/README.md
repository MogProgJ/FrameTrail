# Two remaining fresh-data selector trials

The two completed local controls learned more billboards but added false alarms and broke retention guards. Neither qualified. This package completes the existing four-condition comparison with two M1 trials, seeds17/29. It does not promise improvement.

Run in Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\fresh-selector-batch-20261022-v1\Upload-Package.ps1"
```

Enter KIT OTP/password directly into SCP. This is one upload connection for the ~38MB archive and the literal Bash entry script. The model and old dataset remain reused from the previous KIT package. Uploading does not submit a job.

Then, in an already authenticated KIT terminal:

```bash
bash "$(ws_find frametrail)/FrameTrail/output/START_FRESH_SELECTOR_ON_CLUSTER.sh"
```

This verifies sealed assets, runtime, current authenticated account/QOS/partition/queue evidence and scheduler admission, then submits at most one locked array. Exactly two tasks, at most two concurrent A100s, each2CPU/8GiB/45min,1500updates,1.5allocatedGPUhours maximum in total. Admission is not yet verified locally; missing or denied evidence blocks submission. A recorded job reuses status only. An ambiguous submission retains its lock and cannot create a replacement. No automatic retries, requeues, sweeps or replacement jobs.

Status in that same KIT terminal:

```bash
bash "$(ws_find frametrail)/FrameTrail/output/training-general-v1/rf-fresh-selector-v1/show-output.sh"
```

After both result archives are ready, run Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\fresh-selector-batch-20261022-v1\Retrieve-And-Evaluate.ps1"
```

One SCP connection retrieves both task archives/checksums and the actual job receipt. Structural/hash/schedule/patch checks precede all scoring. Failed tasks remain failed and prevent selection. Local CPU scoring may take several minutes and continues automatically; preserve its window/output. Existing retrieval/evaluation directories intentionally block blind reruns.

## What changes and what stays fixed

Only billboard133 in main and encoder classifiers can learn: mainLR1e-4,encoderLR3e-5,AdamWwd0,noAMP,jointclip.1,unchanged scoped criterion plus geometric dense encoder objective weight1. The exact same1500 four-photo TRAIN schedules pair each GPU trial with its completed CPU control. All other weights, inactive rows, buffers and box regressors remain byte-identical; box outputs can still change when proposal selection changes.

Six prespecified states (0/100/250/500/1000/1500) are saved as tiny row patches. They are scored after retrieval using the existing pinned local Torch2.8.0+cpu scorer. GPU training makes no adaptive decisions and no validation/test predictions. Moving scoring off the allocated GPU avoids idle GPU time and preserves the common scoring runtime. The combined GPU-active plus per-seed deferred CPU validation must remain below1800s; exceeding it makes that seed incomplete. No extension or scoring-device fallback. Finalization remains separately bounded480s.

The cluster receives92fresh TRAIN/validation photographs, but no freshTEST pixels. Training consumes only60freshTRAIN+64oldTRAIN. Validation is167photos, of which32are fresh. Fresh qualification requires at least3extra hits with0extra false alarms, all reviewed-class retention against both original/current baselines and the fixed original unknown cap530. Both seeds of a method must qualify. Rank only by frozen validation F1/hits/fewerFP/earlierstep/lowerglobaltrialindex across all4conditions.

One global winner is locked before known regression checks. If those pass, the32untouched freshTEST photos are consumed once for that winner and the pinned starting reference. The exact veto, frozen before TEST inference, requires >=3additional billboard hits and0extraFP. A failed veto cannot select a runner-up. No winner means no freshTEST inference. Strict ONNX numerical/cost/app qualification remains a separate gate; production adoption is false throughout.

## Evidence and limitations

See `PACKAGE_TEST_REPORT.json`, `BUILT_PACKAGE_CHECK.json`, `TRANSPORT_TEST_REPORT.json`, `POWERSHELL_TEST_REPORT.json` and `unit-test-console.txt`. Checks include actual CPU model load/forward/scoped-loss/backward and patch composition without optimizer updates, immutable input verification, adversarial guards, mocked scheduler/upload flows and actual PowerShell/Bash syntax. No live KIT admission or actual CUDA execution was tested locally. No cluster submission or new fit was performed here. These are assistant code checks, not independent human review.

The first local verifier correctly stopped on sampler-only scene_group metadata added during CPU controls. It was corrected to compare rows exactly against frozen CPU_INPUTS first, then compare original supervision while explicitly accounting for that unchanged grouping and the already reviewed absent overlay. Prior unsubmitted seals/receipts are preserved in `build-history`; no image, target, scope, schedule or scientific hyperparameter changed.

The19Oct strategy specified seeds/pools/four-slot sampler before baseline. Exact schedule files were sealed after baseline and before fits. The unchanged `receipts/EXECUTION_ORDER_NOTE.json` records this ordering deviation; do not claim literal full preregistration. Rights/annotation/scene receipts are assistant-reviewed private-research evidence, not independent human annotation or permission for public redistribution.

Next step: authenticate the single upload and run the cluster entry command, because the remaining paired comparison is ready and live admission must be established on KIT.
