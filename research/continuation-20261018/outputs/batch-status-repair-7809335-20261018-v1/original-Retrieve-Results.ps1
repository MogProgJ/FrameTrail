$ErrorActionPreference = 'Stop'
$taskReceipt = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') | ConvertFrom-Json
if ($taskReceipt.actual_job_id -notmatch '^\d+$' -or @($taskReceipt.archives).Count -ne 4) { throw 'Run Check-Run.ps1 after all four tasks finish; preserve failed-task archives too.' }
if ((@($taskReceipt.archives | ForEach-Object { [int]$_.index } | Sort-Object -Unique) -join ',') -ne '0,1,2,3') { throw 'Need exactly one archive per array index.' }
$taskJob = [string]$taskReceipt.actual_job_id
$taskDestination = Join-Path $PSScriptRoot ('retrieval-' + $taskJob)
if (Test-Path -LiteralPath $taskDestination) { throw 'Retrieval already exists; inspect without overwrite or automatic retry.' }
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskRemote = 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
$taskSources = @()
foreach ($taskRecord in $taskReceipt.archives) {
    if ($taskRecord.index -notin 0,1,2,3 -or $taskRecord.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Invalid archive receipt' }
    $taskName = 'frametrail-rf-billboard-batch-results-' + $taskJob + '_' + $taskRecord.index + '.tar.gz'
    $taskSources += $taskRemote + $taskName
    $taskSources += $taskRemote + $taskName + '.sha256'
}
& scp -o StrictHostKeyChecking=yes @taskSources $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Batch retrieval stopped; preserve partial bytes.' }
foreach ($taskRecord in $taskReceipt.archives) {
    $taskRun = $taskJob + '_' + $taskRecord.index
    $taskName = 'frametrail-rf-billboard-batch-results-' + $taskRun + '.tar.gz'
    $taskLine = (Get-Content -Raw -LiteralPath (Join-Path $taskDestination ($taskName + '.sha256'))).Trim()
    if ($taskLine -notmatch ('^' + $taskRecord.sha256 + '\s+\*?' + [regex]::Escape($taskName) + '$')) { throw 'Server checksum disagrees with completed-task receipt.' }
    $taskVerifiedParent = Join-Path $taskDestination ('task-' + $taskRecord.index)
    New-Item -ItemType Directory -Path $taskVerifiedParent | Out-Null
    & 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'verify_results.py') --archive (Join-Path $taskDestination $taskName) --job $taskRun --expected-sha $taskRecord.sha256 --destination (Join-Path $taskVerifiedParent ('verified-' + $taskRun))
    if ($LASTEXITCODE -ne 0) { throw 'Task structural verification failed; all bytes preserved.' }
}
& 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'compare_batch.py') --retrieval $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Batch comparison needs inspection; no model adopted.' }
