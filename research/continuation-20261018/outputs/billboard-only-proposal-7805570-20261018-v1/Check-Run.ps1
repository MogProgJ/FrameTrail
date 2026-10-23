$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Invoke-KitScript.ps1')
$taskScript = 'set -euo pipefail; cd "$(ws_find frametrail)/FrameTrail"; bash "$PWD/output/training-general-v1/rf-billboard-716ca2cf-v1/show-output.sh"'
$taskResult = Invoke-FrameTrailKitScript -Script $taskScript -LogPath (Join-Path $PSScriptRoot 'latest-output.txt')
$taskJob = [regex]::Match($taskResult.Text, '(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$')
$taskHash = [regex]::Match($taskResult.Text, '(?m)^FRAMETRAIL_ARCHIVE_SHA256=([0-9a-f]{64})\s*$')
if ($taskJob.Success) {
    $taskReceipt = [ordered]@{status='job-recorded-awaiting-results'; actual_job_id=$taskJob.Groups[1].Value; protocol_sha256='716ca2cf411984698e6d096f00fd5ef01995bee9ed4fe0c82a742e26c4bc6e1c'; approved_for_application=$false}
    if ($taskHash.Success) { $taskReceipt.status='archive-ready-awaiting-retrieval'; $taskReceipt.archive_sha256=$taskHash.Groups[1].Value }
    $taskReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') -Encoding utf8
}
if ($taskResult.ExitCode -ne 0) { throw 'Status request failed. No job was submitted by this check.' }
if ($taskHash.Success) { Write-Host 'Archive ready. Run Retrieve-Results.ps1 in this repair folder to download and verify it.' }
