$ErrorActionPreference='Stop'
Write-Host 'FrameTrail: retrieve completed data collection7840599;180pictures; no new jobs.'
Write-Host 'Enter KIT OTP/password directly in this terminal when asked.'
try {
    & (Join-Path $PSScriptRoot 'Retrieve-Data.ps1')
    $taskVerification=Join-Path $PSScriptRoot 'retrieval-7840599\verification-receipt.json'
    $taskResult=Get-Content -Raw -LiteralPath $taskVerification | ConvertFrom-Json
    if ($taskResult.actual_job_id -ne '7840599' -or $taskResult.photos -ne 180 -or $taskResult.status -ne 'data-intake-verified-awaiting-source-identity-content-and-label-review') { throw 'Verified result differs from recorded completion; preserve files.' }
    & 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 -c "import hashlib,pathlib; p=pathlib.Path(r'$PSScriptRoot')/'retrieval-7840599/verified-7840599/output/billboard-data-refresh-7840599/manifest.json'; assert hashlib.sha256(p.read_bytes()).hexdigest()=='0bd27558ab9ae9f5005492db719e90af37883ee9b9577e5fb0a3afa51028fbd8'; print('Manifest matches authenticated cluster report.')"
    if ($LASTEXITCODE -ne 0) { throw 'Pinned manifest differs; preserve evidence.' }
    [pscustomobject]@{status='verified-intake-ready-for-local-review';actual_job_id='7840599';photos=180;approved_for_training=$false;receipt=$taskVerification} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'RETRIEVAL_STATUS.json') -Encoding UTF8
    Write-Host 'Download and structural verification completed. Codex can review the new pictures.'
} catch {
    [pscustomobject]@{status='retrieval-stopped-preserve-evidence';actual_job_id='7840599';error=$_.Exception.Message;approved_for_training=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'RETRIEVAL_STATUS.json') -Encoding UTF8
    Write-Host $_.Exception.Message -ForegroundColor Red
}

