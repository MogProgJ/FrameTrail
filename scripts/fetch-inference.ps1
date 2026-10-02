[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskManifest = Get-Content (Join-Path $taskRoot 'dependencies/windows-onnxruntime.json') -Raw | ConvertFrom-Json
$taskDeps = Join-Path $taskRoot '.deps'
$taskArchive = Join-Path $taskDeps "$($taskManifest.archiveRoot).zip"
$taskPackage = Join-Path $taskDeps $taskManifest.archiveRoot
$taskMarker = Join-Path $taskPackage '.frametrail-sha256'
New-Item -ItemType Directory -Path $taskDeps -Force | Out-Null
if ((Test-Path $taskMarker) -and ((Get-Content $taskMarker -Raw).Trim() -eq $taskManifest.sha256) -and
    (Test-Path (Join-Path $taskPackage 'include/onnxruntime_cxx_api.h'))) {
    Write-Host "ONNX Runtime already present: $taskPackage"
    return
}
if (-not (Test-Path $taskArchive)) {
    Write-Host "Downloading ONNX Runtime $($taskManifest.version) CPU SDK..."
    Invoke-WebRequest $taskManifest.url -OutFile $taskArchive
}
if ((Get-FileHash $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskManifest.sha256) {
    throw 'ONNX Runtime checksum mismatch; inspect the local archive before retrying.'
}
Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskDeps -Force
if (-not (Test-Path (Join-Path $taskPackage 'lib/onnxruntime.dll'))) { throw 'ONNX Runtime DLL missing from archive.' }
Set-Content $taskMarker $taskManifest.sha256 -Encoding ascii
Write-Host "ONNX Runtime ready: $taskPackage"
