$ErrorActionPreference = 'Stop'
$taskFailures = @()
Get-ChildItem -LiteralPath $PSScriptRoot -Filter *.ps1 | ForEach-Object {
    $taskTokens=$null; $taskErrors=$null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$taskTokens,[ref]$taskErrors) | Out-Null
    if ($taskErrors.Count) { $taskFailures += $taskErrors }
}
if ($taskFailures.Count) { $taskFailures | Format-List; throw 'PowerShell syntax failed.' }
Write-Host 'All PowerShell helpers parse successfully.'
