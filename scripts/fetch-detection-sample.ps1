[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskDirectory = Join-Path $taskRoot '.deps/detection-samples'
New-Item -ItemType Directory -Path $taskDirectory -Force | Out-Null
$taskFile = Join-Path $taskDirectory 'dog.jpg'
# Upstream demonstration image; local validation only, not a redistribution fixture.
if (-not (Test-Path $taskFile)) {
    Invoke-WebRequest 'https://raw.githubusercontent.com/Megvii-BaseDetection/YOLOX/6ddff4824372906469a7fae2dc3206c7aa4bbaee/assets/dog.jpg' -OutFile $taskFile
}
if ((Get-FileHash $taskFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne '5a9522051c3cec2bbd2f6323fccba32e8fbf3ddcc2b3e2fd46b04c720bc6f866') {
    throw 'Detection sample checksum mismatch.'
}
Write-Host "Verified detection sample: $taskFile"
