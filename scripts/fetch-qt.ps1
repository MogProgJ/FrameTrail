[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'find-cmake.ps1')
$taskCmake = Find-FrameTrailCMake
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskManifest = Get-Content -LiteralPath (Join-Path $taskRoot 'dependencies/windows-qt.json') -Raw | ConvertFrom-Json
$taskDeps = Join-Path $taskRoot '.deps'
$taskPackage = Join-Path $taskDeps $taskManifest.directory
$taskArchive = Join-Path $taskDeps "qtbase-$($taskManifest.version).7z"
$taskMarker = Join-Path $taskPackage '.frametrail-sha256'
if ((Test-Path -LiteralPath $taskMarker) -and
    ((Get-Content -LiteralPath $taskMarker -Raw).Trim() -eq $taskManifest.sha256) -and
    (Test-Path -LiteralPath (Join-Path $taskPackage 'lib/cmake/Qt6/Qt6Config.cmake'))) {
    Write-Host "Qt SDK already present: $taskPackage"
    return
}
New-Item -ItemType Directory -Path $taskPackage -Force | Out-Null
if (-not (Test-Path -LiteralPath $taskArchive)) {
    Write-Host "Downloading Qt $($taskManifest.version) base SDK (~40 MB)..."
    Invoke-WebRequest -Uri $taskManifest.url -OutFile $taskArchive
}
$taskHash = (Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($taskHash -ne $taskManifest.sha256) { throw "Qt checksum mismatch for $taskArchive" }
Push-Location -LiteralPath $taskPackage
try {
    & $taskCmake -E tar xf $taskArchive
    if ($LASTEXITCODE -ne 0) { throw 'Qt archive extraction failed.' }
} finally { Pop-Location }
if (-not (Test-Path -LiteralPath (Join-Path $taskPackage 'lib/cmake/Qt6/Qt6Config.cmake'))) {
    throw 'The Qt archive did not contain the expected SDK files.'
}
# Official installer archives require this prefix file when extracted manually.
Set-Content -LiteralPath (Join-Path $taskPackage 'bin/qt.conf') -Value "[Paths]`nPrefix=.." -Encoding ascii
Set-Content -LiteralPath $taskMarker -Value $taskManifest.sha256 -Encoding ascii
Write-Host "Qt ready: $taskPackage"
