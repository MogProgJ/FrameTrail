# Existing RF-DETR runtime overlay repair

The corrected SSH transport is working. The new failure is in login-side preflight: `importlib.metadata.PackageNotFoundError: rfdetr`. It occurred after verifying the 965-photo package but before the submission lock and before sbatch, so this attempt did not start a GPU job.

The batch script already exports the existing pinned RF-DETR overlay. The outer login-side wrapper did not. This wrapper loads the **same existing Miniforge module and exact PYTHONPATH from the sealed batch script** before invoking the unchanged guarded submission script. The same environment correction was used before the completed 7780632 trial. There is no pip installation, download, package modification, repeated upload, new scope approval or replacement GPU job.

The package is already extracted and verified. Recovery verifies its seal, reports an existing job if present, refuses a retained ambiguous submission lock, and then performs the original full preflight and one guarded submission.

Run this replacement:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-runtime-repair-20261018-v1\Resume-Approved-Run.ps1"

Enter your KIT OTP/password directly into SSH prompts. One SSH connection is used; the server controls authentication prompts. The expected environment marker is `FRAMETRAIL_PREFLIGHT_OVERLAY=.../output/rf-comparison-v1/python-overlay`.

Use this version's corrected status command afterward:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-runtime-repair-20261018-v1\Check-Run.ps1"

When the result archive is ready:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-runtime-repair-20261018-v1\Retrieve-Results.ps1"

The approved scope remains two classifier rows, at most 2,000 updates, early stop at 1,000 without gain, one A100, 30 active minutes / 45 allocation minutes. Training code, archive, dataset, sampler, model weights and held-out gate are unchanged. New job receipts and retrieval files belong to this repair directory. No GPU job has been submitted by local repair tests. Live KIT preflight can only be confirmed after your authenticated command.
