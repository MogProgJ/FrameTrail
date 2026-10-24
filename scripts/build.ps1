# Full build and all checks:   .\scripts\build.ps1
# Just the app, then open it:   .\scripts\build.ps1 -Run   (skips the test programs and checks)
[CmdletBinding()]
param(
    [ValidateSet('Release', 'Debug')]
    [string]$Configuration = 'Release',
    [switch]$SkipTests,
    [switch]$MediaOnly,
    [switch]$GpuChecks,
    [switch]$Run
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'find-cmake.ps1')
$taskCmake = Find-FrameTrailCMake
$taskCtest = Join-Path (Split-Path -Parent $taskCmake) 'ctest.exe'
$taskManifest = Get-Content -LiteralPath (Join-Path $taskRoot 'dependencies/windows-ffmpeg.json') -Raw | ConvertFrom-Json
$taskFfmpegRoot = Join-Path (Join-Path $taskRoot '.deps') $taskManifest.archiveRoot
$taskQtManifest = Get-Content -LiteralPath (Join-Path $taskRoot 'dependencies/windows-qt.json') -Raw | ConvertFrom-Json
$taskQtRoot = Join-Path (Join-Path $taskRoot '.deps') $taskQtManifest.directory
$taskOrtManifest = Get-Content (Join-Path $taskRoot 'dependencies/windows-onnxruntime.json') -Raw | ConvertFrom-Json
$taskOrtRoot = Join-Path (Join-Path $taskRoot '.deps') $taskOrtManifest.archiveRoot
Push-Location -LiteralPath $taskRoot
try {
    $taskGui = if ($MediaOnly) { 'OFF' } else { 'ON' }
    $taskConfigureArgs = @('--preset', 'windows-msvc', "-DFFMPEG_ROOT=$taskFfmpegRoot", "-DFRAMETRAIL_BUILD_GUI=$taskGui")
    $taskConfigureArgs += "-DONNXRUNTIME_ROOT=$taskOrtRoot"
    $taskConfigureArgs += "-DFRAMETRAIL_TEST_GPU=$(if($GpuChecks){'ON'}else{'OFF'})"
    if (-not $MediaOnly) { $taskConfigureArgs += "-DFRAMETRAIL_QT_ROOT=$taskQtRoot" }
    & $taskCmake @taskConfigureArgs
    if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed. Check the diagnostics above and ensure dependencies were fetched.' }
    $taskBuildArgs = @('--build', '--preset', $Configuration.ToLowerInvariant())
    if ($Run) { $taskBuildArgs += @('--target', 'frametrail-desktop') }
    & $taskCmake @taskBuildArgs
    if ($LASTEXITCODE -ne 0) { throw 'C++ build failed.' }
    if ($Run) {
        $taskApp = Join-Path $taskRoot "build/windows-msvc/$Configuration/frametrail-desktop.exe"
        Start-Process -FilePath $taskApp -WorkingDirectory (Split-Path -Parent $taskApp)
    } elseif (-not $SkipTests) {
        & $taskCtest --preset $Configuration.ToLowerInvariant()
        if ($LASTEXITCODE -ne 0) { throw 'CTest validation failed.' }
    }
} finally {
    Pop-Location
}
