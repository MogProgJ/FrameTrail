$ErrorActionPreference = 'Stop'
$taskHost = 'ka_udxvl@uc3.scc.kit.edu'
$taskArchive = Join-Path $PSScriptRoot 'frametrail-rf-balanced-ddbb57c6-v1.tar.gz'
$taskExpected = '4b06118273e089b6ee283ec3aeb9abcbcc886b3622b7bc3df6df38745660960d'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $taskArchive).Hash.ToLowerInvariant() -ne $taskExpected) { throw 'Local archive changed; no upload.' }
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json')) { Write-Host 'A run receipt exists. Checking the same job without resubmitting.'; & (Join-Path $PSScriptRoot 'Check-Run.ps1'); return }
Write-Host 'Uploading the approved package. Enter KIT OTP/password directly into SSH prompts.'
& scp -o StrictHostKeyChecking=yes $taskArchive ($taskHost + ':/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/frametrail-rf-balanced-ddbb57c6-v1.tar.gz')
if ($LASTEXITCODE -ne 0) { throw 'Upload failed. No submission attempted; no automatic retry.' }
Write-Host 'Verifying and submitting one approved job. KIT may request authentication again.'
$taskScript = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'bootstrap-kit.sh')
$taskLines = @($taskScript | & ssh -T -o StrictHostKeyChecking=yes $taskHost 'tr -d "\015" | bash -l' | Tee-Object -FilePath (Join-Path $PSScriptRoot 'launch-output.txt'))
$taskExit = $LASTEXITCODE
$taskLines | ForEach-Object { Write-Output $_ }
$taskText = $taskLines -join "`n"
$taskMatch = [regex]::Match($taskText, '(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$')
if ($taskMatch.Success) { [pscustomobject]@{status='submitted-or-existing-single-job'; actual_job_id=$taskMatch.Groups[1].Value; protocol_sha256='ddbb57c60855b5499ecdc039642fb5fd527634767e0575507e15b5774131e8c1'; approved_for_application=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') -Encoding utf8 }
if ($taskExit -ne 0) { throw 'Remote command did not finish cleanly. Preserve output and use Check-Run.ps1; do not submit a replacement job.' }
if (-not $taskMatch.Success) { throw 'No job ID captured. Use Check-Run.ps1 to inspect remote state before any repeat.' }
Write-Host ('Job recorded: ' + $taskMatch.Groups[1].Value)
Write-Host 'Next: run Check-Run.ps1 for the job output and completed archive checksum.'
