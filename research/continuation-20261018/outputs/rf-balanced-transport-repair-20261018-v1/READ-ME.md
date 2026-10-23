# Windows PowerShell SSH transport repair

The original launcher used a quoted `tr` pattern. Windows PowerShell 5.1 removed those quotes during native argument serialization; Bash then interpreted the pattern as the literal digits 0, 1 and 5. It deleted those digits from the transmitted script, producing exactly the reported `sha26sum` and `awk {print $}` errors.

The failed command was the initial archive-checksum assignment with `set -euo pipefail`, before extraction and before the submission script. The observed failure therefore did not reach GPU submission. The recovery still checks the existing package identity and retains its persistent one-job submission lock; it never creates a replacement job after an ambiguous submission.

The replacement sends the UTF-8 script as Base64 in a native command with no nested quotes or character-removal filter. It reuses the already uploaded 499 MiB archive: **no SCP and no repeated upload**. The approved training scope, archive and protocol are unchanged. The first remote output marker should retain every digit: `FRAMETRAIL_TRANSPORT_OK=0123456789_sha256sum_$1`.

Run:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-transport-repair-20261018-v1\Resume-Approved-Run.ps1"

Enter your KIT OTP/password directly into the terminal. This resumes the same approved initial submission, or reports the existing job if one is already recorded remotely. A retained lock without a job ID blocks submission and requires inspection.

Use the corrected status command in this repair directory afterward:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-transport-repair-20261018-v1\Check-Run.ps1"

When the archive is ready:

    powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\rf-balanced-transport-repair-20261018-v1\Retrieve-Results.ps1"

New run receipts and retrieval files are written in this repair directory. The earlier prepared package is preserved as historical evidence. This repair changes SSH transport only; it does not change the approved GPU budget, training rows, models, annotations, GUI or held-out gate. A live login still requires your credentials and cannot be completed unattended by Codex.
