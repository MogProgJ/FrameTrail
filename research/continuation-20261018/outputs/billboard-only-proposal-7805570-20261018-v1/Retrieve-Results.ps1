$ErrorActionPreference = 'Stop'
$taskReceipt = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') | ConvertFrom-Json
if ($taskReceipt.actual_job_id -notmatch '^\d+$' -or $taskReceipt.archive_sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Run Check-Run.ps1 first to record the actual job and completed archive checksum.' }
$taskJob = [string]$taskReceipt.actual_job_id
$taskExpected = [string]$taskReceipt.archive_sha256
$taskArchive = 'frametrail-rf-billboard-results-' + $taskJob + '.tar.gz'
$taskDestination = Join-Path $PSScriptRoot ('retrieval-' + $taskJob)
if (Test-Path -LiteralPath $taskDestination) { throw 'Retrieval exists. Preserve it for inspection; no overwrite or automatic retry.' }
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskRemote = 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
& scp -o StrictHostKeyChecking=yes ($taskRemote + $taskArchive + '.sha256') (Join-Path $taskDestination ($taskArchive + '.sha256'))
if ($LASTEXITCODE -ne 0) { throw 'Checksum download failed; partial folder preserved.' }
$taskSidecar = (Get-Content -Raw -LiteralPath (Join-Path $taskDestination ($taskArchive + '.sha256'))).Trim()
if ($taskSidecar -notmatch ('^' + $taskExpected + '\s+\*?' + [regex]::Escape($taskArchive) + '$')) { throw 'Server checksum differs from the recorded completed-job output.' }
& scp -o StrictHostKeyChecking=yes ($taskRemote + $taskArchive) (Join-Path $taskDestination $taskArchive)
if ($LASTEXITCODE -ne 0) { throw 'Archive download failed; partial folder preserved.' }
& 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'verify_results.py') --archive (Join-Path $taskDestination $taskArchive) --job $taskJob --expected-sha $taskExpected
if ($LASTEXITCODE -ne 0) { throw 'Result verification failed; bytes preserved for inspection.' }
Write-Host 'Retrieved and structurally verified. Audit the selection before held-out scoring, export or adoption.'
