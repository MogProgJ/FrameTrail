[CmdletBinding()]
param([ValidateSet('s','m','all','openimages')][string]$Size='m', [string]$Python)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
if(-not $Python){$Python=Join-Path $taskRoot '.deps/recognition-python/Scripts/python.exe'}
$taskSizes=if($Size -eq 'all'){@('s','m')}else{@($Size)}
foreach($taskSize in $taskSizes) {
    $taskProfile=if($taskSize -eq 'openimages'){'openimages'}else{"world-$taskSize"}
    $taskManifest=Get-Content -LiteralPath (Join-Path $taskRoot "dependencies/yolo-$taskProfile.json") -Raw | ConvertFrom-Json
    $taskModel=Join-Path $taskRoot "models/$($taskManifest.filename)"
    if(Test-Path -LiteralPath $taskModel) {
        if((Get-FileHash -LiteralPath $taskModel).Hash.ToLowerInvariant() -ne $taskManifest.sha256){throw 'Installed recognition model checksum mismatch; inspect it before retrying.'}
        Write-Host "Verified expanded recognition model: $taskModel";continue
    }
    if(-not (Test-Path -LiteralPath $Python)){throw 'Expanded recognition export needs the optional developer environment. See docs/RECOGNITION.md. Packaged app needs no Python.'}
    $taskWeightsDirectory=Join-Path $taskRoot '.deps/world-export/weights'
    New-Item -ItemType Directory -Path $taskWeightsDirectory,(Join-Path $taskRoot 'models') -Force | Out-Null
    $taskWeights=Join-Path $taskWeightsDirectory ([IO.Path]::GetFileName($taskManifest.weights_url))
    if(-not (Test-Path -LiteralPath $taskWeights)) {
        $taskDownload=$taskWeights+'.download'
        try {
            Invoke-WebRequest $taskManifest.weights_url -OutFile $taskDownload
            if((Get-FileHash -LiteralPath $taskDownload).Hash.ToLowerInvariant() -ne $taskManifest.weights_sha256){throw 'Official checkpoint checksum mismatch.'}
            Move-Item -LiteralPath $taskDownload -Destination $taskWeights
        } finally {if(Test-Path -LiteralPath $taskDownload){Remove-Item -LiteralPath $taskDownload}}
    }
    if((Get-FileHash -LiteralPath $taskWeights).Hash.ToLowerInvariant() -ne $taskManifest.weights_sha256){throw 'Checkpoint checksum mismatch.'}
    $taskExport=Join-Path $taskRoot ('models/world-'+[Guid]::NewGuid().ToString('N')+'.onnx')
    & $Python -B (Join-Path $PSScriptRoot 'export-world.py') --weights $taskWeights --profile $taskProfile --output $taskExport
    if($LASTEXITCODE -ne 0){throw 'Recognition export failed. Existing models were preserved.'}
    if((Get-FileHash -LiteralPath $taskExport).Hash.ToLowerInvariant() -ne $taskManifest.sha256){throw "Export checksum differs from the pinned artifact; retained for inspection: $taskExport"}
    Move-Item -LiteralPath $taskExport -Destination $taskModel
    Move-Item -LiteralPath ([IO.Path]::ChangeExtension($taskExport,'.export.json')) -Destination ([IO.Path]::ChangeExtension($taskModel,'.export.json'))
    Write-Host "Exported and verified recognition model: $taskModel"
}
