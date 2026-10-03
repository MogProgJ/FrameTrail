[CmdletBinding()]
param([ValidateSet('nano','small','all')][string]$Model = 'nano')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskDirectory = Join-Path $taskRoot 'models'
New-Item -ItemType Directory -Path $taskDirectory -Force | Out-Null
$taskModels = if ($Model -eq 'all') { @('nano','small') } else { @($Model) }
foreach ($taskVariant in $taskModels) {
    $taskManifest = Get-Content (Join-Path $taskRoot "dependencies/yolox-$taskVariant.json") -Raw | ConvertFrom-Json
    $taskFile = Join-Path $taskDirectory $taskManifest.filename
    if (-not (Test-Path -LiteralPath $taskFile)) {
        $taskDownload = $taskFile + '.' + [Guid]::NewGuid().ToString('N') + '.download'
        try {
            Write-Host "Downloading $($taskManifest.name)..."
            Invoke-WebRequest $taskManifest.url -OutFile $taskDownload
            if ((Get-FileHash -LiteralPath $taskDownload).Hash.ToLowerInvariant() -ne $taskManifest.sha256) { throw 'Downloaded model checksum mismatch.' }
            Move-Item -LiteralPath $taskDownload -Destination $taskFile
        } finally {
            if (Test-Path -LiteralPath $taskDownload) { Remove-Item -LiteralPath $taskDownload }
        }
    }
    if ((Get-FileHash -LiteralPath $taskFile).Hash.ToLowerInvariant() -ne $taskManifest.sha256) { throw "Model checksum mismatch. Inspect $taskFile before retrying." }
    Write-Host "Verified detection model: $taskFile"
}
