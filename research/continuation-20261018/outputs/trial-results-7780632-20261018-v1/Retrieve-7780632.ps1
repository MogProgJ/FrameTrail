$ErrorActionPreference = 'Stop'
$taskJob = '7780632'
$taskExpected = 'ae4fcd247566cc0a9c2abe81f8e25a61626e1987d1f950d8af5ddecc2db8a3ff'
$taskArchive = 'frametrail-rf-nextdata-results-7780632.tar.gz'
$taskRemote = 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
$taskDestination = Join-Path $PSScriptRoot 'retrieval'
if (Test-Path -LiteralPath $taskDestination) { throw 'Retrieval already exists. Preserve it and ask Codex to inspect it before retrying.' }
New-Item -ItemType Directory -Path $taskDestination | Out-Null
& scp ($taskRemote + $taskArchive + '.sha256') (Join-Path $taskDestination ($taskArchive + '.sha256'))
if ($LASTEXITCODE -ne 0) { throw 'Checksum download failed. Partial retrieval preserved; no automatic retry.' }
$taskSidecar = (Get-Content -LiteralPath (Join-Path $taskDestination ($taskArchive + '.sha256')) -Raw).Trim()
if ($taskSidecar -notmatch ('^' + $taskExpected + '\s+\*?' + [regex]::Escape($taskArchive) + '$')) { throw 'Remote checksum differs from the user-reported job output. Stop and inspect.' }
& scp ($taskRemote + $taskArchive) (Join-Path $taskDestination $taskArchive)
if ($LASTEXITCODE -ne 0) { throw 'Archive download failed. Partial retrieval preserved; no automatic retry.' }
$taskActual = (Get-FileHash -LiteralPath (Join-Path $taskDestination $taskArchive) -Algorithm SHA256).Hash.ToLower()
if ($taskActual -ne $taskExpected) { throw 'Archive SHA256 does not match the completed job output.' }
$taskPython = 'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-cpu\Scripts\python.exe'
& $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'verify_results.py') --archive (Join-Path $taskDestination $taskArchive) --job $taskJob
if ($LASTEXITCODE -ne 0) { throw 'Result verification failed; original bytes preserved.' }
Write-Output 'Job 7780632 retrieved and structurally verified. Export, held-out evaluation and app adoption remain separate steps.'
