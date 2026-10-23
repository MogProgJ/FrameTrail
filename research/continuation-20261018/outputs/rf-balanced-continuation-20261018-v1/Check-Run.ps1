$ErrorActionPreference = 'Stop'
$taskRemoteScript = 'set -euo pipefail; cd "$(ws_find frametrail)/FrameTrail"; bash "$PWD/output/training-general-v1/rf-balanced-ddbb57c6-v1/show-output.sh"'
$taskLines = @($taskRemoteScript | & ssh -T -o StrictHostKeyChecking=yes ka_udxvl@uc3.scc.kit.edu 'tr -d "\015" | bash -l' | Tee-Object -FilePath (Join-Path $PSScriptRoot 'latest-output.txt'))
if ($LASTEXITCODE -ne 0) { throw 'Status request failed. No training job was submitted by this check.' }
$taskLines | ForEach-Object { Write-Output $_ }
$taskText = $taskLines -join "`n"
$taskJob = [regex]::Match($taskText, '(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$')
$taskHash = [regex]::Match($taskText, '(?m)^FRAMETRAIL_ARCHIVE_SHA256=([0-9a-f]{64})\s*$')
if ($taskJob.Success) {
  $taskReceipt = [ordered]@{status='job-recorded-awaiting-results'; actual_job_id=$taskJob.Groups[1].Value; protocol_sha256='ddbb57c60855b5499ecdc039642fb5fd527634767e0575507e15b5774131e8c1'; approved_for_application=$false}
  if ($taskHash.Success) { $taskReceipt.status='archive-ready-awaiting-retrieval'; $taskReceipt.archive_sha256=$taskHash.Groups[1].Value }
  $taskReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') -Encoding utf8
}
if ($taskHash.Success) { Write-Host 'Archive ready. Run Retrieve-Results.ps1 to download and verify it.' }
