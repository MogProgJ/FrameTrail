# Approved FrameTrail balanced continuation

**Approved and locally verified; not submitted.** KIT requires a fresh interactive OTP/password login. The unattended access check returned `Permission denied (publickey,keyboard-interactive)`. Run this in your own PowerShell terminal and enter credentials directly into the SSH prompts:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-continuation-20261018-v1\Launch-Approved-Run.ps1"

This uploads the SHA-pinned 498.5 MiB package, verifies every package asset, checks the pinned KIT runtime and original model, and submits at most one job. A persistent remote submission lock prevents a duplicate if the connection closes after sbatch. A lock without a job receipt requires Slurm-history inspection, never an automatic replacement job. The interactive login itself cannot be tested without your credentials.

The protocol bytes are unchanged from the approved proposal (SHA256 `ddbb57c60855b5499ecdc039642fb5fd527634767e0575507e15b5774131e8c1`). Historical proposal-status fields are superseded by the separate approval.json recording your explicit instruction to proceed.

Only final classifier rows 133 and 593 may update, starting at old job 7780632 step 600 with a fresh AdamW optimizer at .0001. Each update has one billboard-positive, one washing-machine-positive and two explicitly negative training photos. Maximum 2,000 updates; stop at 1,000 if no eligible strict gain. One A100, 30-minute active-command timeout, 45-minute Slurm allocation. No retries, model downloads, threshold changes or automatic app adoption.

All scored per-class counts and aggregate unknown-prediction totals must reproduce both pinned baselines. Per-class unscored distributions may differ: those are not false positives. Retention still guards every reviewed class's complete TP/FP and partial hits, plus the original aggregate unknown-drift limit of five. No agreed guard was relaxed.

The package contains the exact 965-photo release and evidence, starting checkpoint and frozen reference predictions. Test photos are hash-checked as assets, never used for training, selection or inference. The existing pretrained RF model is reused at its pinned KIT location; none is downloaded.

Check the exact submitted job output with:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-continuation-20261018-v1\Check-Run.ps1"

When that reports a completed archive, download and structurally verify it with:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-continuation-20261018-v1\Retrieve-Results.ps1"

Run receipts, terminal-output receipts and retrieval directories are created by those future commands. The preparatory hash manifest covers prepared files only. Audit selection before held-out scoring. Export and app adoption remain separate gates. The current app, GUI package, source, prior cohorts and vocabulary are unchanged; the deleted older MiniERP copy is never referenced.
