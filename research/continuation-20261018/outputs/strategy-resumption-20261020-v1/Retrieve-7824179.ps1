$ErrorActionPreference='Stop'
$taskPackage='C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\billboard-data-refresh-7818553-20261018-v1'
$taskReceipt=Get-Content -Raw -LiteralPath (Join-Path $taskPackage 'run-receipt.json') | ConvertFrom-Json
if ($taskReceipt.actual_job_id -ne '7824179' -or $taskReceipt.archive_sha256 -ne '306d770895e4c03df1d4e1fbc8a0b00189456518a0619a81a664d97189994a77') { throw 'Pinned job/hash differ; stopped.' }
Write-Host 'FrameTrail: retrieve completed data collection 7824179.'
Write-Host 'Enter KIT OTP/password directly here when SSH asks. No new cluster job will be submitted.'
try {
    & (Join-Path $taskPackage 'Retrieve-Data.ps1')
    $taskVerification=Join-Path $taskPackage 'retrieval-7824179\verification-receipt.json'
    if (-not (Test-Path -LiteralPath $taskVerification)) { throw 'Verification receipt was not created; preserve all downloaded files.' }
    $taskResult=Get-Content -Raw -LiteralPath $taskVerification | ConvertFrom-Json
    if ($taskResult.actual_job_id -ne '7824179' -or $taskResult.status -ne 'data-intake-verified-awaiting-source-identity-content-and-label-review' -or $taskResult.photos -ne 240) { throw 'Returned intake differs from the completed report; preserve it for inspection.' }
    [pscustomobject]@{status='verified-intake-ready-for-local-review';actual_job_id='7824179';photos=240;receipt=$taskVerification;approved_for_training=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'RETRIEVAL_STATUS.json') -Encoding UTF8
    Write-Host 'Download and structural verification finished. Codex can now review the pictures locally.'
} catch {
    [pscustomobject]@{status='retrieval-stopped-preserve-evidence';actual_job_id='7824179';error=$_.Exception.Message;approved_for_training=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'RETRIEVAL_STATUS.json') -Encoding UTF8
    Write-Host $_.Exception.Message -ForegroundColor Red
}
