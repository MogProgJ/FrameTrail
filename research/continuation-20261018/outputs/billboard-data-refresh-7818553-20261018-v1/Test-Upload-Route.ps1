$ErrorActionPreference='Stop'
$global:frameTrailUploadMockCalls=@()
function global:scp {
    $global:frameTrailUploadMockCalls+=,@($args)
    $global:LASTEXITCODE=0
}
try {
    & (Join-Path $PSScriptRoot 'Upload-Data-Package.ps1')
    if ($global:frameTrailUploadMockCalls.Count -ne 1) { throw 'Expected one inert SCP invocation.' }
    $taskArgs=$global:frameTrailUploadMockCalls[0]
    $taskReceipt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'archive-receipt.json') | ConvertFrom-Json
    if ($taskArgs.Count -ne 5 -or $taskArgs[2] -ne (Join-Path $PSScriptRoot $taskReceipt.archive) -or $taskArgs[3] -ne (Join-Path $PSScriptRoot $taskReceipt.cluster_start_script)) { throw 'Expected archive plus start script in the same SCP invocation.' }
    Write-Output 'PASS: one inert SCP invocation containing both files; zero network connections or submissions.'
} finally {
    Remove-Item Function:\scp
    Remove-Variable -Name frameTrailUploadMockCalls -Scope Global
}
