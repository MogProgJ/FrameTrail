$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Invoke-KitScript.ps1')
$taskOriginal = 'C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/rf-balanced-continuation-20261018-v1'
$taskArchive = Join-Path $taskOriginal 'frametrail-rf-balanced-ddbb57c6-v1.tar.gz'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $taskArchive).Hash.ToLowerInvariant() -ne '4b06118273e089b6ee283ec3aeb9abcbcc886b3622b7bc3df6df38745660960d') { throw 'Original local package changed. Stop before remote action.' }
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json')) { Write-Host 'Run receipt exists; checking the same job without submission.'; & (Join-Path $PSScriptRoot 'Check-Run.ps1'); return }
Write-Host 'Reusing the package already uploaded to KIT. No SCP or replacement job is created by this recovery.'
Write-Host 'Enter KIT OTP/password directly in the terminal when SSH requests them.'
$taskScript = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'resume-kit.sh')
$taskResult = Invoke-FrameTrailKitScript -Script $taskScript -LogPath (Join-Path $PSScriptRoot 'resume-output.txt')
$taskMatch = [regex]::Match($taskResult.Text, '(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$')
if ($taskMatch.Success) { [pscustomobject]@{status='submitted-or-existing-single-job'; actual_job_id=$taskMatch.Groups[1].Value; protocol_sha256='ddbb57c60855b5499ecdc039642fb5fd527634767e0575507e15b5774131e8c1'; approved_for_application=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') -Encoding utf8 }
if ($taskResult.ExitCode -ne 0) { throw 'Remote recovery stopped. Preserve resume-output.txt and inspect it; do not submit a replacement job.' }
if (-not $taskMatch.Success) { throw 'No job ID returned. Run the corrected Check-Run.ps1 to inspect remote state before repeating.' }
Write-Host ('Recorded approved job: ' + $taskMatch.Groups[1].Value)
Write-Host 'Next: run Check-Run.ps1 in this repair folder to obtain the exact job output.'
