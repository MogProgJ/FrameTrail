[CmdletBinding()]
param(
    [ValidateSet('Release', 'Debug')]
    [string]$Configuration = 'Release',
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskCmakeCommand = Get-Command cmake -ErrorAction SilentlyContinue
$taskCmake = if ($taskCmakeCommand) { $taskCmakeCommand.Source } else { $null }
if (-not $taskCmake) {
    $taskVswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (Test-Path -LiteralPath $taskVswhere) {
        $taskCandidates = @(& $taskVswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.CMake.Project -find '**/cmake.exe')
        if ($taskCandidates.Count -gt 0) { $taskCmake = $taskCandidates[0] }
    }
}
if (-not $taskCmake) {
    throw 'CMake not found. Install Visual Studio 2022 Desktop development with C++ (including CMake), or add CMake 3.25+ to PATH.'
}
$taskCtest = Join-Path (Split-Path -Parent $taskCmake) 'ctest.exe'
$taskManifest = Get-Content -LiteralPath (Join-Path $taskRoot 'dependencies/windows-ffmpeg.json') -Raw | ConvertFrom-Json
$taskFfmpegRoot = Join-Path (Join-Path $taskRoot '.deps') $taskManifest.archiveRoot
Push-Location -LiteralPath $taskRoot
try {
    & $taskCmake --preset windows-msvc "-DFFMPEG_ROOT=$taskFfmpegRoot"
    if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed. Check the diagnostics above and ensure dependencies were fetched.' }
    & $taskCmake --build --preset $Configuration.ToLowerInvariant()
    if ($LASTEXITCODE -ne 0) { throw 'C++ build failed.' }
    if (-not $SkipTests) {
        & $taskCtest --preset $Configuration.ToLowerInvariant()
        if ($LASTEXITCODE -ne 0) { throw 'CTest validation failed.' }
    }
} finally {
    Pop-Location
}
