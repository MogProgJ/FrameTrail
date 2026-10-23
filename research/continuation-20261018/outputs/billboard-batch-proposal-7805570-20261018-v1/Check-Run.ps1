$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Invoke-KitScript.ps1')
$taskScript = 'set -euo pipefail; cd "$(ws_find frametrail)/FrameTrail"; bash "$PWD/output/training-general-v1/rf-billboard-batch-0a255598-v1/show-output.sh"'
$taskResult = Invoke-FrameTrailKitScript -Script $taskScript -LogPath (Join-Path $PSScriptRoot 'latest-output.txt')
if ($taskResult.ExitCode -ne 0) { throw 'Status failed; no new submission.' }
$taskJob = [regex]::Match($taskResult.Text, '(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$')
if ($taskJob.Success) {
    $taskArchives = @([regex]::Matches($taskResult.Text, '(?m)(?:^|(?<=\}))FRAMETRAIL_TASK_ARCHIVE=([0-3]):([0-9a-f]{64})\s*$') | ForEach-Object { [ordered]@{index=[int]$_.Groups[1].Value; sha256=$_.Groups[2].Value} })
    [ordered]@{actual_job_id=$taskJob.Groups[1].Value;protocol_sha256='0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd';archives=$taskArchives;approved_for_application=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') -Encoding utf8
    if ($taskArchives.Count -eq 4) { Write-Host 'All four archives are ready. Run Retrieve-Results.ps1 once for the full batch.' }
}
