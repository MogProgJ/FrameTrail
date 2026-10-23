$ErrorActionPreference='Stop'
Write-Host 'FrameTrail targeted intake: 180 new candidates; one CPU job; zero GPUs; no training.'
Write-Host 'This window only uploads the verified package. Enter KIT OTP/password directly here.'
try {
    & (Join-Path $PSScriptRoot 'Upload-Data-Package.ps1')
    [pscustomobject]@{status='upload-complete-awaiting-existing-cluster-session-launch';remote_directory='data-refresh-658b0c2c-v1';cluster_submitted=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'UPLOAD_STATUS.json') -Encoding UTF8
    Write-Host 'Run this in your ALREADY OPEN cluster terminal:' -ForegroundColor Green
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'CLUSTER_COMMAND.txt') | Write-Host
} catch {
    [pscustomobject]@{status='upload-stopped-preserve-evidence';error=$_.Exception.Message;cluster_submitted=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'UPLOAD_STATUS.json') -Encoding UTF8
    Write-Host $_.Exception.Message -ForegroundColor Red
}

