[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskManifest = Get-Content (Join-Path $taskRoot 'dependencies/sqlite.json') -Raw | ConvertFrom-Json
$taskDeps = Join-Path $taskRoot '.deps'
$taskArchive = Join-Path $taskDeps "$($taskManifest.archiveRoot).zip"
$taskPackage = Join-Path $taskDeps $taskManifest.archiveRoot
New-Item -ItemType Directory -Path $taskDeps -Force | Out-Null
if (-not (Test-Path $taskArchive)) {
    Invoke-WebRequest $taskManifest.url -OutFile $taskArchive
}
if ((Get-FileHash $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskManifest.sha256) {
    throw 'SQLite checksum mismatch; inspect the archive before retrying.'
}
Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskDeps -Force
if (-not (Test-Path (Join-Path $taskPackage 'sqlite3.c'))) { throw 'SQLite source missing.' }
Write-Host "SQLite $($taskManifest.version) source ready: $taskPackage"
