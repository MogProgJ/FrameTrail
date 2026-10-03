[CmdletBinding()]
param([Parameter(Mandatory)][string]$PackageDirectory, [Parameter(Mandatory)][string]$InputFile, [switch]$GpuChecks)
$ErrorActionPreference = 'Stop'
$taskPackage = (Resolve-Path -LiteralPath $PackageDirectory).Path
$taskInput = (Resolve-Path -LiteralPath $InputFile).Path
if ($taskInput.Contains('"')) { throw 'Unsupported quote in input path.' }
$taskManifest = Get-Content -LiteralPath (Join-Path $taskPackage 'manifest.json') -Raw | ConvertFrom-Json
foreach ($taskFile in $taskManifest.files) {
    $taskPath = [IO.Path]::GetFullPath((Join-Path $taskPackage $taskFile.path))
    if (-not $taskPath.StartsWith($taskPackage + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid manifest path.' }
    if ((Get-FileHash -LiteralPath $taskPath).Hash.ToLowerInvariant() -ne $taskFile.sha256) { throw "Package hash mismatch: $($taskFile.path)" }
}
$taskOldPath = $env:PATH
$taskOldPlatform = $env:QT_QPA_PLATFORM
$taskOldPlugins = $env:QT_PLUGIN_PATH
$taskOldPlatformPlugins = $env:QT_QPA_PLATFORM_PLUGIN_PATH
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:QT_QPA_PLATFORM = 'offscreen'
    $env:QT_PLUGIN_PATH = ''
    $env:QT_QPA_PLATFORM_PLUGIN_PATH = ''
    Push-Location -LiteralPath $env:TEMP
    try {
        & (Join-Path $taskPackage 'frametrail.exe') inspect $taskInput --detect (Join-Path $taskPackage 'models/yolox_nano.onnx') --max-frames 3
        if ($LASTEXITCODE -ne 0) { throw 'Packaged CLI decode/inference failed.' }
        if (Test-Path -LiteralPath (Join-Path $taskPackage 'models/yolox_s.onnx')) {
            & (Join-Path $taskPackage 'frametrail.exe') inspect $taskInput --detect (Join-Path $taskPackage 'models/yolox_s.onnx') --model-type small --max-frames 3
            if ($LASTEXITCODE -ne 0) { throw 'Packaged YOLOX-S inference failed.' }
        }
        foreach($taskProfile in @('world-s','world-m','openimages')) {
            $taskRecognition=Get-Content -LiteralPath (Join-Path $taskPackage "dependencies/yolo-$taskProfile.json") -Raw | ConvertFrom-Json
            $taskRecognitionModel=Join-Path $taskPackage "models/$($taskRecognition.filename)"
            if(Test-Path -LiteralPath $taskRecognitionModel) {
                & (Join-Path $taskPackage 'frametrail.exe') inspect $taskInput --detect $taskRecognitionModel --model-type $taskProfile --max-frames 3
                if($LASTEXITCODE -ne 0){throw 'Packaged expanded CPU recognition failed.'}
                if($GpuChecks) {
                    & (Join-Path $taskPackage 'frametrail.exe') inspect $taskInput --detect $taskRecognitionModel --model-type $taskProfile --backend directml --max-frames 3
                    if($LASTEXITCODE -ne 0){throw 'Packaged expanded GPU recognition failed.'}
                }
            }
        }
        if($GpuChecks) {
            foreach($taskProfile in @('nano','small')) {
                $taskModelName=if($taskProfile -eq 'nano'){'yolox_nano.onnx'}else{'yolox_s.onnx'}
                & (Join-Path $taskPackage 'frametrail.exe') inspect $taskInput --detect (Join-Path $taskPackage "models/$taskModelName") --model-type $taskProfile --backend directml --max-frames 3
                if($LASTEXITCODE -ne 0) { throw 'Strict packaged GPU inference failed.' }
            }
        }
        $taskApp = Start-Process -FilePath (Join-Path $taskPackage 'frametrail-desktop.exe') -ArgumentList @('--smoke-test', ('"' + $taskInput + '"')) -PassThru -WindowStyle Hidden
        if (-not $taskApp.WaitForExit(30000)) { $taskApp.Kill(); throw 'Packaged GUI startup timed out.' }
        if ($taskApp.ExitCode -ne 0) { throw "Packaged GUI decode/presentation failed: $($taskApp.ExitCode)" }
    } finally { Pop-Location }
} finally {
    $env:PATH = $taskOldPath
    $env:QT_QPA_PLATFORM = $taskOldPlatform
    $env:QT_PLUGIN_PATH = $taskOldPlugins
    $env:QT_QPA_PLATFORM_PLUGIN_PATH = $taskOldPlatformPlugins
}
Write-Host 'Package hashes, CLI inference and offscreen GUI passed with development PATH removed. No camera was opened.'
