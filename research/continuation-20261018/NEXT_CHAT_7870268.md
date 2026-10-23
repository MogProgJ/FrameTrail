# Superseded: local evaluation already completed

Read NEXT_CHAT_7870268_EVALUATED.md and outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md. Do not rerun the command below. All four conditions complete; no eligible model; TEST untouched. A separate TRAIN-only study scope decision is next.

---

# Preserved historical handoff

# Continue FrameTrail: verified completed batch7870268, local evaluation next

User explicitly requested continuing in a new chat after renewing SSH. This handoff is the current action point. Read this file, AGENTS.md beside it and the first section of CURRENT_HANDOFF.md. Older paragraphs below separators are historical snapshots.

## Working boundary and autonomy

Canonical continuation folder: C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation. Saved project label FrameTrail currently points at an unrelated MiniERP folder; DO NOT edit MiniERP. Do all output work under this continuation. Source app/dependencies are readable under C:/Users/nazee/Documents/All Modules/FrameTrail. User permits continuous local work and bounded cluster continuation within established exact scope; pause only for real human interaction such as expired KIT login, unavailable credentials, or consequential unresolved scope. No routine approval prompts. Do not spawn subagents without explicit authorization. End every response/update with the single best concrete next FrameTrail step and why; plain language. Training strategy primary, app secondary.

Strictly ignore Carrington Event and all other projects' jobs/files/logs/results/environments/sessions. Shared SSH account is not permission. Target only FrameTrail receipt-verified job IDs and paths, not username/name alone. No broad scheduler management, cancelling/requeuing/reprioritizing other work, replacing failed jobs, or freeing their resources. Preserve unrelated keys. No automation/monitor exists.

## Just completed in sending chat

Key-only access restored and independently verified via network-escalated BatchMode SSH. Normal sandbox DNS previously fails; use appropriate require_escalated network operations if needed, with strict host checks and prompts disabled. Do not ask for pasted OTP/password/private key. Dedicated Windows agent identity and host config work. If later expired, user runs existing outputs/cluster-access-20261022-v1/Start-Work-Session.ps1 directly; no new key/registration. Avoid unnecessary unlocks while current access works.

Actual FrameTrail array7870268, tasks0/1, both COMPLETED exit0:0, scheduler elapsed12m59s each. Actual start2026-10-22T20:00:17 per scheduler. Both1500updates, seeds17/29. Reported active471.00039734799066s /469.33869404302095s. Both frozen-state/inactive-row flags true; no validation selection or TEST inference on cluster. These are structural/runtime results, not performance evidence.

Downloaded both archives+sidecars+submitted-job-id.txt using key-only SCP. Exact ID7870268 confirmed. Safe extraction/hash/scope/job/schedule/rowpatch/dtype/shape/1500training-update/admission checks succeeded. Verification receipt:

C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/fresh-selector-batch-20261022-v1/retrieval/VERIFICATION.json

Both tasks status complete-structurally-verified-awaiting-local-selection, all_complete=true. Extracted folders verified-7870268_0 and verified-7870268_1 in that retrieval directory. No evaluation started; no local-evaluation directory created by sending chat. No running processes/sessions to inherit. Do not invoke Retrieve-And-Evaluate.ps1 again: it intentionally refuses an existing retrieval directory. Do NOT reretrieve, resubmit, reseal or retrain.

Archive0 SHA499e7cb4313ed83144f21bae81b41b9f24a745c4c6d3cd7579fce4151edd884f.
Archive1 SHA2d1001f329e168127bba3348b8cc790cf89d552f6429c2bf729ca9be3ef8c6a5.
ScopeSHA a8cc4ce065bb300869f85e416b48f56fd3ecf8cf00e25db2b08abef9dfaaeb3f.
Package sealSHA b3b48c9ccb5cfe867cbd03e2dbba86ac35b9e26b269f535c343b44168699fcf4.
Starting checkpointSHA c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3.
Both remote frozen-state digests214d4ba84414fe25c8f8b138c6e0270e440a0351576d08be0a7d36b106d2c5ae; local pipeline must independently reproduce starting-state identity.

## Exact next command: local CPU evaluation only

Run through exec_command, preserving console output to a new file and a running session while it works. No network or credentials needed for this stage. All authorized; do not pause to ask permission.

```powershell
& 'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-cpu\Scripts\python.exe' -u -B -X utf8 'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\fresh-selector-batch-20261022-v1\local_followup.py' --downloads 'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\fresh-selector-batch-20261022-v1\retrieval' --job 7870268
```

Uses pinned Torch2.8.0+cpu/rfdetr1.11.2,2CPUthreads,MATH attention, strict determinism, and all117 local input hashes. No optimizer steps. Fullforward M1 scoring (cannot use frozen-decoder caches after encoder changes). Validation167photos =old135+fresh32, each of5newstates perseed. Step0 can reuse pinned prior metrics only after exact checkpoint/row/data identity. May take several minutes. Send concise meaningful progress updates at most60sec apart; don't change scoring device or thresholds for speed.

Combined GPU-active + local per-seed validation must remain<1800s; leaves about1329s forseed17 /1330.66s forseed29. Script enforces this; a partial seed is incomplete, no budget extensions/retries/replacements. If deterministic/software errors arise, preserve receipts and partial outputs, diagnose/fix only valid local orchestration; never silently rerun consumed TEST or change scientific gates. Existing exclusive evaluation/consumption locks must be honored.

## Frozen scientific design and gates

Remaining M1 two-head-row trials use same exact TRAIN four-slot schedules as completed M0 controls. Only billboard133 main+encoder rows train; LR1e-4/3e-5,AdamWwd0,clip.1,noAMP,existing scoped criterion+dense geometry objective1. Other parameters/buffers/inactive rows/box regressors frozen bitwise. Proposal changes can change box outputs. Saved patches0/100/250/500/1000/1500. No additional sweep/unfreezing/new fit.

Four conditions total: M0 main-only CPUseeds17/29 already finished and failed qualification; M1main+encoder GPUseeds17/29 now ready for same pinned CPU scorer. M0at500 yielded4TP2FP /5TP2FP,at1000both9TP7FP,at1500 11TP8FP /10TP8FP. Oldunknowncap also breached. Neither retained model; do not adopt later states just for morehits.

Fresh baseline0TP/0FP/14FN on32freshVAL;77other-class detections unscored, not billboardFP. Qualifying checkpoint requires >=3additionalfreshbillboardhits,0extraFP,all reviewed-class retention against BOTH original/current old baselines and original fixed unknown cap530 (not533). Both seeds of a method must qualify and complete before that method is eligible. Rank globalwinner acrossall4conditions on freshF1,hits,fewerFP,earlierstep,lowerglobaltrialindex. Winner locked BEFORE known-regression checks. Then freshTEST32once/veto only if known-regression passes: candidate>=startingreferenceTESThits+3 and0extraFP; no runner-up substitution. If no eligible method, retain starting model and do not consume TEST. Separate strictONNX/cost/app gates remain; production_adoption=false throughout.

Qualified data124photos/68targets/124identifiedscenes: TRAIN30positive/38targets+30absent;VAL12positive/14targets+20absent;TEST12positive/16targets+20absent. Frozen manifest b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09 under outputs/data-review-7840599-20261021-v1/reviewed-release-v1. Source/rights/whole-photo completeness/scene reviews and readiness complete, assistant-reviewed private research, not independent human annotation. Preserve roles/targets/source hashes; unknown classes never background. No curation after baseline.

Important honest execution note:19Oct TRAIN pools/seeds/four-slot rule fixed before baseline, but exact schedule files sealed AFTERbaseline and BEFOREfits. EXECUTION_ORDER_NOTE.json records it. Do not backdate or call literal fully preregistered implementation. Schedule17 d831162e01329f216a33ce8fa241dfe5f9207fd1a168611befef9d53e3438f5b; schedule29 177ccf3955c7df8b8c480a576a9274276abf50da38ade5fdb8ada17a4153fdbd.

## After local result

Read retrieval/local-evaluation/FINAL_REPORT.json and GLOBAL_SELECTION.json. Explain in ordinary language whether both seeds improved cleanly, which gates failed/passed, and what that means. Continue already-authorized local diagnostics/qualification where justified; do not present trial completion as success. Existing pipeline/test artifacts: PACKAGE_TEST_REPORT.json, BUILT_PACKAGE_CHECK.json, TRANSPORT_TEST_REPORT.json, POWERSHELL_TEST_REPORT.json;8guardgroups +actual4fixtureCPUloss/backward/patch checks pass. Additional10synthetic postrun-rule tests pass under outputs/while-cluster-runs-20261022-v1, no realTEST use. Actual CUDA execution now completed inboth tasks. Training focus remains primary; current productionapp/defaultYOLOX/RFpreview/ONNXhold untouched.

Next step: run the existing local_followup.py on the verified retrieval, because both completed seeds must pass the same validation/retention rules before any candidate advances.
