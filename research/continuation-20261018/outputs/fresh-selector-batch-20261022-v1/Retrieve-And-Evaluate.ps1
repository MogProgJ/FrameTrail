$ErrorActionPreference='Stop'
$taskPython='C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-cpu\Scripts\python.exe'
$taskBase=Join-Path $PSScriptRoot 'rf-fresh-selector-v1'
$taskDownloads=Join-Path $PSScriptRoot 'retrieval'
if (Test-Path -LiteralPath $taskDownloads) { throw 'Retrieval already exists; preserve it. Inspect saved state before any further action.' }
New-Item -ItemType Directory -Path $taskDownloads | Out-Null
$taskRemote='ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/training-general-v1/rf-fresh-selector-v1'
Write-Host 'Retrieving both task archives and the actual job receipt in one SCP connection. Enter KIT authentication directly.'
& scp -o StrictHostKeyChecking=yes ($taskRemote+'/submitted-job-id.txt') ($taskRemote+'/results/task-0.tar.gz') ($taskRemote+'/results/task-0.tar.gz.sha256') ($taskRemote+'/results/task-1.tar.gz') ($taskRemote+'/results/task-1.tar.gz.sha256') $taskDownloads
if ($LASTEXITCODE -ne 0) { throw 'Retrieval incomplete; bytes preserved. No job resubmission or automatic retry.' }
$taskJob=(Get-Content -Raw -LiteralPath (Join-Path $taskDownloads 'submitted-job-id.txt')).Trim()
if ($taskJob -notmatch '^[1-9][0-9]*$') { throw 'Actual numeric array job receipt required.' }
foreach ($taskIndex in 0,1) {
  Rename-Item -LiteralPath (Join-Path $taskDownloads ('task-'+$taskIndex+'.tar.gz')) -NewName ('frametrail-fresh-selector-results-'+$taskJob+'_'+$taskIndex+'.tar.gz')
  Rename-Item -LiteralPath (Join-Path $taskDownloads ('task-'+$taskIndex+'.tar.gz.sha256')) -NewName ('frametrail-fresh-selector-results-'+$taskJob+'_'+$taskIndex+'.tar.gz.sha256')
}
& $taskPython -B -X utf8 (Join-Path $taskBase 'verify_results.py') --base $taskBase --downloads $taskDownloads --job $taskJob
if ($LASTEXITCODE -ne 0) { throw 'Result verification failed; preserve all bytes.' }
& $taskPython -u -B -X utf8 (Join-Path $PSScriptRoot 'local_followup.py') --downloads $taskDownloads --job $taskJob
if ($LASTEXITCODE -ne 0) { throw 'Local evaluation stopped; preserve evidence. Do not rerun consumed TEST or change selection.' }
Write-Host ('Done. Inspect '+(Join-Path $taskDownloads 'local-evaluation\FINAL_REPORT.json'))
