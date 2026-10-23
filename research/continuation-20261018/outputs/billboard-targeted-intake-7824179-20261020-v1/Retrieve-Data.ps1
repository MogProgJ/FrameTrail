$ErrorActionPreference='Stop'
$taskReceipt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') | ConvertFrom-Json
if ($taskReceipt.actual_job_id -notmatch '^\d+$' -or $taskReceipt.archive_sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Import the cluster completion output first; exact job/hash required.' }
$taskJob=[string]$taskReceipt.actual_job_id
$taskDestination=Join-Path $PSScriptRoot ('retrieval-'+$taskJob)
if (Test-Path -LiteralPath $taskDestination) { throw 'Existing retrieval preserved; inspect without retry/overwrite.' }
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskName='frametrail-data-refresh-results-'+$taskJob+'.tar.gz'
& scp -o StrictHostKeyChecking=yes ('ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'+$taskName+'*') $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Transfer stopped; preserve bytes.' }
$taskNames=@(Get-ChildItem -LiteralPath $taskDestination -File | ForEach-Object { $_.Name })
if (@(Compare-Object @($taskName,($taskName+'.sha256')) $taskNames).Count -ne 0) { throw 'Unexpected transfer files.' }
$taskLine=(Get-Content -Raw -LiteralPath (Join-Path $taskDestination ($taskName+'.sha256'))).Trim()
if ($taskLine -notmatch ('^'+$taskReceipt.archive_sha256+'\s+\*?'+[regex]::Escape($taskName)+'$')) { throw 'Server sidecar differs from the recorded cluster hash.' }
& 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'verify_results.py') --archive (Join-Path $taskDestination $taskName) --job $taskJob --expected-sha $taskReceipt.archive_sha256
if ($LASTEXITCODE -ne 0) { throw 'Data verification failed; preserve all files.' }
