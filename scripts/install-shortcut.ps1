# Adds "FrameTrail" to the desktop and the Start menu. Both open the built app directly:
# no terminal and no build, so it starts at once. Run again any time; it overwrites its own shortcuts.
[CmdletBinding()]
param([switch]$Quiet)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskApp = Join-Path $taskRoot 'build\windows-msvc\Release\frametrail-desktop.exe'
if (-not (Test-Path -LiteralPath $taskApp)) { throw 'The app is not built yet. Run Update-FrameTrail.cmd or .\scripts\build.ps1 -AppOnly first.' }
$taskShell = New-Object -ComObject WScript.Shell
foreach ($taskFolder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
    $taskPath = Join-Path $taskFolder 'FrameTrail.lnk'
    $taskLink = $taskShell.CreateShortcut($taskPath)
    $taskLink.TargetPath = $taskApp
    $taskLink.WorkingDirectory = Split-Path -Parent $taskApp
    $taskLink.IconLocation = "$taskApp,0"
    $taskLink.Description = 'FrameTrail: detect, track and count objects in videos and photos'
    $taskLink.Save()
    if (-not $Quiet) { Write-Host "Created $taskPath" }
}
