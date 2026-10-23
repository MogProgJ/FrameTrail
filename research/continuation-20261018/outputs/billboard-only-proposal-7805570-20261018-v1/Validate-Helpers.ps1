$ErrorActionPreference = 'Stop'
$taskResults = @()
foreach ($taskFile in (Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' -File)) {
    $taskTokens = $null
    $taskErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($taskFile.FullName,[ref]$taskTokens,[ref]$taskErrors) | Out-Null
    if ($taskErrors.Count -gt 0) { throw ($taskFile.Name + ': ' + ($taskErrors | Out-String)) }
    $taskResults += $taskFile.Name
}
[pscustomobject]@{status='Windows-PowerShell-5.1-syntax-passed';files=$taskResults} | ConvertTo-Json
