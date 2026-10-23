# Current approved FrameTrail batch

This handoff supersedes the unapproved draft status in HANDOFF.md, CONTINUATION_STATE.json and preparation/proposal snapshots. Those files are historical and intentionally preserved. The user explicitly approved the exact four-trial batch: "All right, I approve the four trial batch to proceed to the next stage with all the previous instructions."

Approval is recorded separately in `C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\billboard-batch-proposal-7805570-20261018-v1\rf-billboard-batch-0a255598-v1\approval.json` and APPROVAL_RECEIPT.json. Protocol SHA-256: `0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd`. Core data/code and proposal scope are unchanged.

Approved scope: one four-task Slurm array 0-3%2, regular gpu_a100_il. Each task: one A100, two CPUs,8GiB host memory,45minutes wall,<=3000updates,<=1800seconds training process and<=480seconds known-regression processing. Maximum two concurrent A100s and three aggregate requested GPU-hours. No retries, requeue or replacement jobs. Matrix is1:1 versus1:3 positive/explicit-negative photos at learning rates.0001 and.0003. Start job7805570 selectedstep100; update only billboard row133, freeze all other model parameters. Same sealed data, thresholds, guards and validation-only selection.

The package `frametrail-rf-billboard-batch-0a255598-v1.tar.gz` is ready: 531662532bytes, SHA-256`4d8eb2e3fddda53f0d404fa3956662660bca7c69258066623bf60fac79d2543a`. Independent archive reading verified all 3017 member identities and hashes against the core seal plus separate approval; there are no extra members. Bootstrap has the exact archive and seal hashes with all placeholders resolved. All earlier12CPU/structural and6mock-Slurm checks remain applicable. No real GPU inference or model training was performed locally.

No SSH connection, upload or new submission has occurred. Real array ID is unknown. Direct KIT OTP/password authentication is the remaining human input. The launcher runs scheduler/account queries and sbatch --test-only before the single real submission. If rejected, stop and inspect the recorded evidence. If response is ambiguous, preserve launch-output.txt and use Check-Run.ps1; never automatically re-run submission or create a replacement. Scheduler limits remain unverified until authenticated checks run.

Launch command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\billboard-batch-proposal-7805570-20261018-v1\Launch-Approved-Run.ps1"
```

After submission, Check-Run.ps1 records actual root array ID and four task archive checksums. Retrieve-Results.ps1 retrieves/verifies all four in one invocation. Continue the independent validation rescoring, selection replay and frozen/inactive tensor audit locally before accepting a provisional winner. Known regression outcomes must not reselect a checkpoint/variant; old references are consumed, not fresh independent tests. Local audit/export/parity/reversible integration/packaging require no routine approval. Preserve all older data/models/receipts/builds and failed task evidence.

Existing selected model remains job7805570step100 (washing3/15, billboard0/19 known targets). Existing strict ONNX numerical hold is unchanged; native preview is explicit, standard default YOLOX-S preserved, production_adoption=false. Training is not a fix for runtime numerical qualification.

Next step: run the approved launcher and enter KIT authentication directly, because the approved package is sealed and submission now needs authenticated access.
