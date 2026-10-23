$ErrorActionPreference = 'Stop'
$taskReceipt = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') | ConvertFrom-Json
if ($taskReceipt.actual_job_id -notmatch '^\d+$' -or @($taskReceipt.archives).Count -ne 4) { throw 'Run Check-Run.ps1 after all four tasks finish; preserve failed-task archives too.' }
if ((@($taskReceipt.archives | ForEach-Object { [int]$_.index } | Sort-Object -Unique) -join ',') -ne '0,1,2,3') { throw 'Need exactly one archive per array index.' }
$taskJob = [string]$taskReceipt.actual_job_id
$taskDestination = Join-Path $PSScriptRoot ('retrieval-' + $taskJob)
if (Test-Path -LiteralPath $taskDestination) { throw 'Retrieval already exists; inspect without overwrite or automatic retry.' }
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskRemote = 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
# One fixed SFTP glob source lets OpenSSH retrieve the eight batch files in one connection.
$taskSource = $taskRemote + 'frametrail-rf-selector-results-' + $taskJob + '_[0-3].tar.gz*'
& scp -o StrictHostKeyChecking=yes $taskSource $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Batch retrieval stopped; preserve partial bytes.' }
$taskExpectedNames = @($taskReceipt.archives | ForEach-Object {
    $taskBaseName = 'frametrail-rf-selector-results-' + $taskJob + '_' + $_.index + '.tar.gz'
    $taskBaseName
    $taskBaseName + '.sha256'
})
$taskDownloadedNames = @(Get-ChildItem -LiteralPath $taskDestination -File | ForEach-Object { $_.Name })
if (@(Compare-Object $taskExpectedNames $taskDownloadedNames).Count -ne 0) { throw 'Need exactly the four expected archives and four sidecars; preserve downloaded bytes.' }
foreach ($taskRecord in $taskReceipt.archives) {
    if ($taskRecord.index -notin 0,1,2,3 -or $taskRecord.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Invalid archive receipt' }
    $taskRun = $taskJob + '_' + $taskRecord.index
    $taskName = 'frametrail-rf-selector-results-' + $taskRun + '.tar.gz'
    $taskLine = (Get-Content -Raw -LiteralPath (Join-Path $taskDestination ($taskName + '.sha256'))).Trim()
    if ($taskLine -notmatch ('^' + $taskRecord.sha256 + '\s+\*?' + [regex]::Escape($taskName) + '$')) { throw 'Server checksum disagrees with completed-task receipt.' }
    $taskVerifiedParent = Join-Path $taskDestination ('task-' + $taskRecord.index)
    New-Item -ItemType Directory -Path $taskVerifiedParent | Out-Null
    & 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'verify_results.py') --archive (Join-Path $taskDestination $taskName) --job $taskRun --expected-sha $taskRecord.sha256 --destination (Join-Path $taskVerifiedParent ('verified-' + $taskRun))
    if ($LASTEXITCODE -ne 0) { throw 'Task structural verification failed; all bytes preserved.' }
}
& 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'compare_batch.py') --retrieval $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Batch comparison needs inspection; no model adopted.' }
$taskAudit = (Join-Path $PSScriptRoot 'audit_batch.py')
Write-Host 'Running the independent local CPU audit of all four trials. No new cluster job or model adoption.'
& 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 $taskAudit --retrieval $taskDestination --output (Join-Path $taskDestination 'independent-audit')
if ($LASTEXITCODE -ne 0) { throw 'Independent batch audit failed; preserve all returned files for inspection. No model adopted.' }
