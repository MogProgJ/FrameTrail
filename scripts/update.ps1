# Get the latest FrameTrail code, rebuild only the desktop app, refresh the shortcuts and open it.
# Double-click Update-FrameTrail.cmd in the FrameTrail folder, or run:  .\scripts\update.ps1
[CmdletBinding()]
param([switch]$NoLaunch)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskApp = Join-Path $taskRoot 'build\windows-msvc\Release\frametrail-desktop.exe'
# The build replaces the .exe, which Windows does not allow while it is running.
$taskRunning = Get-Process -Name 'frametrail-desktop' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $taskApp }
if ($taskRunning) { throw 'FrameTrail is open. Close it (save any analysis you want to keep), then run the update again.' }
Push-Location -LiteralPath $taskRoot
try {
    Write-Host 'Getting the latest FrameTrail code...'
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Getting the latest code failed; the message above says why.' }
    Write-Host 'Rebuilding the app (only the parts that changed; up to a few minutes after large updates)...'
    & (Join-Path $PSScriptRoot 'build.ps1') -AppOnly
    & (Join-Path $PSScriptRoot 'install-shortcut.ps1') -Quiet
    Write-Host 'FrameTrail is up to date.'
    if (-not $NoLaunch) { Start-Process -FilePath $taskApp -WorkingDirectory (Split-Path -Parent $taskApp) }
} finally {
    Pop-Location
}
