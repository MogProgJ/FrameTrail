function Invoke-FrameTrailKitScript {
    param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$LogPath)
    $taskBytes = [System.Text.Encoding]::UTF8.GetBytes($Script.Replace("`r",''))
    $taskPayload = [Convert]::ToBase64String($taskBytes)
    if ($taskPayload -notmatch '^[A-Za-z0-9+/=]+$') { throw 'Unexpected transport alphabet.' }
    # No nested quotes, digit-removal filter, or piped script stdin. This form
    # survives Windows PowerShell 5.1 native argument serialization.
    $taskCommand = 'printf %s ' + $taskPayload + ' | base64 -d | bash -l'
    $taskLines = @(& ssh -T -o StrictHostKeyChecking=yes ka_udxvl@uc3.scc.kit.edu $taskCommand | Tee-Object -FilePath $LogPath)
    $taskExit = $LASTEXITCODE
    foreach ($taskLine in $taskLines) { Write-Host $taskLine }
    return [pscustomobject]@{ExitCode=$taskExit; Lines=$taskLines; Text=($taskLines -join "`n")}
}
