[CmdletBinding()]
param([switch]$MediaOnly)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskManifest = Get-Content -LiteralPath (Join-Path $taskRoot 'dependencies/windows-ffmpeg.json') -Raw | ConvertFrom-Json
$taskDeps = Join-Path $taskRoot '.deps'
$taskArchive = Join-Path $taskDeps "$($taskManifest.archiveRoot).zip"
$taskPackage = Join-Path $taskDeps $taskManifest.archiveRoot
New-Item -ItemType Directory -Path $taskDeps -Force | Out-Null

# Do not trust a partial install. A marker is written only after hash verification
# and extraction; the build also checks that headers and libraries are present.
$taskMarker = Join-Path $taskPackage '.frametrail-sha256'
if ((Test-Path -LiteralPath $taskMarker) -and
    ((Get-Content -LiteralPath $taskMarker -Raw).Trim() -eq $taskManifest.sha256)) {
    Write-Host "Verified dependency already present: $taskPackage"
} else {
    if (-not (Test-Path -LiteralPath $taskArchive)) {
        Write-Host "Downloading FFmpeg $($taskManifest.version) (~81 MB)..."
        Invoke-WebRequest -Uri $taskManifest.url -OutFile $taskArchive
    }
    $taskHash = (Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($taskHash -ne $taskManifest.sha256) {
        throw "FFmpeg checksum mismatch. Expected $($taskManifest.sha256), got $taskHash. Inspect the archive at $taskArchive before retrying."
    }
    Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskDeps -Force
    if (-not (Test-Path -LiteralPath (Join-Path $taskPackage 'include/libavcodec/avcodec.h'))) {
        throw 'The verified archive did not contain the expected FFmpeg development headers.'
    }
    Set-Content -LiteralPath $taskMarker -Value $taskManifest.sha256 -Encoding ascii
    Write-Host "FFmpeg ready: $taskPackage"
    Write-Host 'This local development dependency is ignored by Git; its bundled license files remain in .deps.'
}
if (-not $MediaOnly) { & (Join-Path $PSScriptRoot 'fetch-qt.ps1') }
& (Join-Path $PSScriptRoot 'fetch-inference.ps1')
& (Join-Path $PSScriptRoot 'fetch-model.ps1')
& (Join-Path $PSScriptRoot 'fetch-storage.ps1')
