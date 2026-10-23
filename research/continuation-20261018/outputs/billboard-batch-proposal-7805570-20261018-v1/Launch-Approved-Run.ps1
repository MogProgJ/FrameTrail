$ErrorActionPreference = 'Stop'
$taskIdentity = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'PROPOSAL_IDENTITY.json') | ConvertFrom-Json
$taskTools = Join-Path $PSScriptRoot $taskIdentity.package_directory
if (-not (Test-Path -LiteralPath (Join-Path $taskTools 'approval.json'))) { throw 'Explicit approval for this exact cluster job is required before packaging or SSH. No job submitted.' }
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'archive-receipt.json'))) {
    & 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'prepare_archive.py')
    if ($LASTEXITCODE -ne 0) { throw 'Approved archive preparation failed; preserve the output and inspect it.' }
}
$taskArchive = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'archive-receipt.json') | ConvertFrom-Json
$taskPath = Join-Path $PSScriptRoot $taskArchive.archive
if ((Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskArchive.archive_sha256) { throw 'Archive checksum differs; no upload.' }
. (Join-Path $PSScriptRoot 'Invoke-KitScript.ps1')
Write-Host 'Uploading the approved four-trial billboard array package. Enter KIT OTP/password directly into SSH prompts.'
& scp -o StrictHostKeyChecking=yes $taskPath 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
if ($LASTEXITCODE -ne 0) { throw 'Upload stopped. No automatic retry or replacement job.' }
$taskScript = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'bootstrap-approved.sh')
$taskResult = Invoke-FrameTrailKitScript -Script $taskScript -LogPath (Join-Path $PSScriptRoot 'launch-output.txt')
$taskJob = [regex]::Match($taskResult.Text,'(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$')
if ($taskJob.Success) {
    [ordered]@{status='submitted-or-existing-single-job';actual_job_id=$taskJob.Groups[1].Value;protocol_sha256=$taskIdentity.protocol_sha256;approved_for_application=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') -Encoding utf8
    Write-Host ('Recorded approved job: '+$taskJob.Groups[1].Value)
}
if ($taskResult.ExitCode -ne 0) { throw 'Submission response failed or is ambiguous. Preserve launch-output.txt and use Check-Run.ps1; do not submit a replacement.' }
if (-not $taskJob.Success) { throw 'No job receipt returned. Inspect the saved log; no automatic retry.' }
Write-Host 'Next: Check-Run.ps1 follows this actual job.'
