[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskManifest = Get-Content (Join-Path $taskRoot 'dependencies/yolox-nano.json') -Raw | ConvertFrom-Json
$taskDirectory = Join-Path $taskRoot 'models'
$taskFile = Join-Path $taskDirectory $taskManifest.filename
New-Item -ItemType Directory -Path $taskDirectory -Force | Out-Null
if (-not (Test-Path $taskFile)) {
    Write-Host 'Downloading YOLOX-Nano (~3.6 MB)...'
    Invoke-WebRequest $taskManifest.url -OutFile $taskFile
}
if ((Get-FileHash $taskFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskManifest.sha256) {
    throw "Model checksum mismatch. Inspect $taskFile before retrying."
}
Write-Host "Verified detection model: $taskFile"
