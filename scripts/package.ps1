[CmdletBinding()]
param([string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskBuild = Join-Path $taskRoot 'build/windows-msvc/Release'
$taskQtManifest = Get-Content (Join-Path $taskRoot 'dependencies/windows-qt.json') -Raw | ConvertFrom-Json
$taskQt = Join-Path (Join-Path $taskRoot '.deps') $taskQtManifest.directory
$taskFfmpegManifest = Get-Content (Join-Path $taskRoot 'dependencies/windows-ffmpeg.json') -Raw | ConvertFrom-Json
$taskFfmpeg = Join-Path (Join-Path $taskRoot '.deps') $taskFfmpegManifest.archiveRoot
$taskOrtManifest = Get-Content (Join-Path $taskRoot 'dependencies/windows-onnxruntime.json') -Raw | ConvertFrom-Json
$taskOrt = Join-Path (Join-Path $taskRoot '.deps') $taskOrtManifest.archiveRoot
$taskModelManifest = Get-Content (Join-Path $taskRoot 'dependencies/yolox-nano.json') -Raw | ConvertFrom-Json
$taskModel = Join-Path $taskRoot 'models/yolox_nano.onnx'
if ((Get-FileHash -LiteralPath $taskModel).Hash.ToLowerInvariant() -ne $taskModelManifest.sha256) { throw 'Model checksum mismatch.' }
foreach ($taskName in @('frametrail.exe','frametrail-desktop.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskBuild $taskName))) { throw 'Build Release with GUI enabled first: scripts/build.ps1' }
}
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $taskRoot ('out/FrameTrail-0.9.0-win64-' + (Get-Date -Format 'yyyyMMdd-HHmmss')) }
if ((Test-Path -LiteralPath $OutputDirectory) -or (Test-Path -LiteralPath ($OutputDirectory + '.zip'))) { throw 'Choose a new package directory. Existing packages are never overwritten.' }
$taskStage = (New-Item -ItemType Directory -Path $OutputDirectory).FullName
foreach ($taskName in @('frametrail.exe','frametrail-desktop.exe')) { Copy-Item -LiteralPath (Join-Path $taskBuild $taskName) -Destination $taskStage }
Get-ChildItem -LiteralPath (Join-Path $taskFfmpeg 'bin') -Filter '*.dll' | Copy-Item -Destination $taskStage
Copy-Item -LiteralPath (Join-Path $taskOrt 'lib/onnxruntime.dll') -Destination $taskStage
& (Join-Path $taskQt 'bin/windeployqt.exe') --release --no-translations --no-compiler-runtime --dir $taskStage (Join-Path $taskStage 'frametrail-desktop.exe')
if ($LASTEXITCODE -ne 0) { throw 'Qt deployment failed; incomplete staging directory retained for inspection.' }
# Include the offscreen plugin solely for the documented file-only deployment check.
Copy-Item -LiteralPath (Join-Path $taskQt 'plugins/platforms/qoffscreen.dll') -Destination (Join-Path $taskStage 'platforms')
# App-local release CRT, from the installed Visual Studio redistributable directory.
$taskVswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$taskVs = & $taskVswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $taskVs) { throw 'Visual Studio C++ redistributable directory not found.' }
$taskCrt = Get-ChildItem -Path (Join-Path $taskVs 'VC/Redist/MSVC/*/x64/Microsoft.VC143.CRT') -Directory | Sort-Object FullName -Descending | Select-Object -First 1
if (-not $taskCrt) { throw 'MSVC x64 release CRT not found.' }
Get-ChildItem -LiteralPath $taskCrt.FullName -Filter '*.dll' | Copy-Item -Destination $taskStage
New-Item -ItemType Directory -Path (Join-Path $taskStage 'models'),(Join-Path $taskStage 'notices'),(Join-Path $taskStage 'dependencies') | Out-Null
Copy-Item -LiteralPath $taskModel -Destination (Join-Path $taskStage 'models')
$taskSmallManifest = Get-Content (Join-Path $taskRoot 'dependencies/yolox-small.json') -Raw | ConvertFrom-Json
$taskSmallModel = Join-Path $taskRoot ('models/' + $taskSmallManifest.filename)
if (Test-Path -LiteralPath $taskSmallModel) {
    if ((Get-FileHash -LiteralPath $taskSmallModel).Hash.ToLowerInvariant() -ne $taskSmallManifest.sha256) { throw 'YOLOX-S checksum mismatch.' }
    Copy-Item -LiteralPath $taskSmallModel -Destination (Join-Path $taskStage 'models')
}
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'dependencies') -Filter '*.json' | Copy-Item -Destination (Join-Path $taskStage 'dependencies')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs/PACKAGING.md') -Destination (Join-Path $taskStage 'README.md')
$taskGuide = Join-Path $taskStage 'README.md'
$taskGuideText = (Get-Content -LiteralPath $taskGuide -Raw).Replace('](SAVED_RUNS.md)','](docs/SAVED_RUNS.md)')
Set-Content -LiteralPath $taskGuide -Value $taskGuideText -Encoding utf8
$taskDocs = New-Item -ItemType Directory -Path (Join-Path $taskStage 'docs')
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'docs') -Filter '*.md' | Copy-Item -Destination $taskDocs.FullName
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs/benchmarks') -Destination $taskDocs.FullName -Recurse
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs/THIRD_PARTY_NOTICES.md') -Destination (Join-Path $taskStage 'notices')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs/notices') -Destination (Join-Path $taskStage 'notices/upstream') -Recurse
Copy-Item -LiteralPath (Join-Path $taskFfmpeg 'LICENSE.txt') -Destination (Join-Path $taskStage 'notices/FFmpeg-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $taskOrt 'LICENSE') -Destination (Join-Path $taskStage 'notices/ONNXRuntime-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $taskOrt 'ThirdPartyNotices.txt') -Destination (Join-Path $taskStage 'notices/ONNXRuntime-ThirdPartyNotices.txt')
Copy-Item -LiteralPath (Join-Path $taskQt 'sbom') -Destination (Join-Path $taskStage 'notices/Qt-SBOM') -Recurse
@('[Paths]','Prefix=.','Plugins=.') | Set-Content -LiteralPath (Join-Path $taskStage 'qt.conf') -Encoding ascii
$taskFiles = @(Get-ChildItem -LiteralPath $taskStage -File -Recurse | Sort-Object FullName | ForEach-Object {
    [ordered]@{ path = $_.FullName.Substring($taskStage.Length + 1).Replace('\','/'); bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant() }
})
[ordered]@{ version = '0.9.0'; channel = 'private-preview'; created_utc = [DateTime]::UtcNow.ToString('o'); files = $taskFiles } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskStage 'manifest.json') -Encoding utf8
Compress-Archive -Path (Join-Path $taskStage '*') -DestinationPath ($taskStage + '.zip') -CompressionLevel Optimal
(Get-FileHash -LiteralPath ($taskStage + '.zip')).Hash | Set-Content -LiteralPath ($taskStage + '.zip.sha256') -Encoding ascii
Write-Host "Private preview package: $taskStage.zip"
