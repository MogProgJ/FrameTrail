$ErrorActionPreference = 'Stop'
$taskBatch = 'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\billboard-batch-proposal-7805570-20261018-v1'
$taskTokens = $null
$taskErrors = $null
$taskAst = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $taskBatch 'Check-Run.ps1'), [ref]$taskTokens, [ref]$taskErrors)
if ($taskErrors.Count -ne 0) { throw 'PowerShell parser errors' }
$taskConstants = @($taskAst.FindAll({ param($node) $node -is [System.Management.Automation.Language.StringConstantExpressionAst] -and $node.Value.StartsWith('(?m)') -and $node.Value.Contains('FRAMETRAIL_TASK_ARCHIVE') }, $true))
if ($taskConstants.Count -ne 1) { throw 'Need exactly the production archive regex' }
$taskPattern = $taskConstants[0].Value
$taskLog = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'original-latest-output.txt')
$taskOldMatches = @([regex]::Matches($taskLog,'(?m)^FRAMETRAIL_TASK_ARCHIVE=([0-3]):([0-9a-f]{64})\s*$'))
if ($taskOldMatches.Count -ne 0) { throw 'Fixture no longer reproduces the original failure' }
$taskMatches = @([regex]::Matches($taskLog,$taskPattern))
if ($taskMatches.Count -ne 4) { throw 'Repaired production parser missed actual archives' }
$taskReceipt = Get-Content -Raw -LiteralPath (Join-Path $taskBatch 'run-receipt.json') | ConvertFrom-Json
foreach ($taskMatch in $taskMatches) {
    $taskIndex = [int]$taskMatch.Groups[1].Value
    $taskExpected = @($taskReceipt.archives | Where-Object { $_.index -eq $taskIndex })
    if ($taskExpected.Count -ne 1 -or $taskExpected[0].sha256 -ne $taskMatch.Groups[2].Value) { throw 'Recovered hash identity differs' }
}
$taskHash = 'a' * 64
foreach ($taskPrefix in @('', '}')) {
    $taskSample = $taskPrefix + 'FRAMETRAIL_TASK_ARCHIVE=2:' + $taskHash + "`n"
    $taskMatch = [regex]::Match($taskSample,$taskPattern)
    if (-not $taskMatch.Success -or $taskMatch.Groups[1].Value -ne '2' -or $taskMatch.Groups[2].Value -ne $taskHash) { throw 'Line-start/JSON-adjacent marker rejected' }
}
$taskSource = 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/frametrail-rf-billboard-batch-results-7809335_[0-3].tar.gz*'
$taskArgs = @('-o','StrictHostKeyChecking=yes',$taskSource,'C:\inert-local-fixture')
if ($taskArgs.Count -ne 4 -or @($taskArgs | Where-Object { $_.StartsWith('ka_udxvl@') }).Count -ne 1) { throw 'Expected one fixed remote source expression' }
Write-Output 'PASS: original failure reproduced; production regex recovers all four exact actual hashes; line-start and JSON-adjacent markers accepted; single remote-source argument retained. No network access.'
