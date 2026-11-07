# Install a model trained in the cloud (Kaggle, a rented machine) into the app, from the downloaded results.
# Run from the FrameTrail folder:
#   powershell -ExecutionPolicy Bypass -File training\cloud\install-model.ps1 -From "$HOME\Downloads"
# -From is a folder or a .zip that holds rfdetr_openimages.onnx and rfdetr_openimages.json somewhere inside
# (Kaggle's results folder, or the whole downloaded output). The model is installed only if it passed its ONNX check.
# The model already installed (for example the pilot) is kept as models\rfdetr_openimages-<its run name>.onnx.
# The score files go to runs\<Run>\ so they stay next to the earlier runs.
param(
    [Parameter(Mandatory = $true)][string]$From,
    [string]$Run = 'full-small'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path $From)) { throw "Not found: $From" }

$source = (Resolve-Path $From).Path
if ($source -like '*.zip') {
    $unpacked = Join-Path ([IO.Path]::GetTempPath()) ("frametrail-model-" + [guid]::NewGuid())
    Write-Output "Unpacking $source ..."
    Expand-Archive -Path $source -DestinationPath $unpacked
    $source = $unpacked
}
# The newest model under the folder; a copy inside a results folder wins over other copies of the same age.
$model = Get-ChildItem -Path $source -Recurse -Filter 'rfdetr_openimages.onnx' -File |
    Sort-Object @{ Expression = { $_.Directory.Name -eq 'results' }; Descending = $true }, @{ Expression = 'LastWriteTime'; Descending = $true } |
    Select-Object -First 1
if (-not $model) { if ($unpacked) { Remove-Item -Recurse -Force $unpacked }; throw "No rfdetr_openimages.onnx under $source. Download keep\results from the Kaggle output first." }
$folder = $model.Directory.FullName
$summaryFile = Join-Path $folder 'rfdetr_openimages.json'
if (-not (Test-Path $summaryFile)) { throw "rfdetr_openimages.json is missing next to $($model.FullName); download it too." }
$summary = Get-Content -Raw $summaryFile | ConvertFrom-Json
if (-not $summary.parity.passed) { throw 'This model failed its ONNX check (parity.passed is not true), so it was not installed.' }
Write-Output "Model: $($model.FullName)"
Write-Output "Name: $($summary.metadata.'frametrail.name'); classes: $($summary.classes); ONNX check passed."

# Scores and the model, kept with the other runs.
$runFolder = Join-Path $repo "runs\$Run"
New-Item -ItemType Directory -Force $runFolder | Out-Null
foreach ($name in @('rfdetr_openimages.onnx', 'rfdetr_openimages.json', 'eval-test.json', 'compare-baseline.md', 'metrics.csv',
                    'metrics-part1.csv', 'metrics-part2.csv', 'runs.jsonl', 'training_config.json', 'warmstart.json')) {
    $file = Join-Path $folder $name
    if (Test-Path $file) { Copy-Item -Force $file (Join-Path $runFolder $name) }
}
$baseline = Join-Path $folder 'baseline-eval-test.json'
if (Test-Path $baseline) {
    $target = Join-Path $repo 'runs\baseline-yolov8s-oiv7-full'
    New-Item -ItemType Directory -Force $target | Out-Null
    Copy-Item -Force $baseline (Join-Path $target 'eval-test.json')
}
Write-Output "Saved the scores in $runFolder"

# The app finds models in models\ next to its executable; build.ps1 copies models\ there too.
foreach ($target in @((Join-Path $repo 'models'), (Join-Path $repo 'build\windows-msvc\Release\models'))) {
    if ($target -like '*Release*' -and -not (Test-Path (Split-Path -Parent $target))) { continue }
    New-Item -ItemType Directory -Force $target | Out-Null
    $installed = Join-Path $target 'rfdetr_openimages.onnx'
    if (Test-Path $installed) {
        if ((Get-FileHash $installed).Hash -eq (Get-FileHash $model.FullName).Hash) {
            Write-Output "Already installed: $installed"
            continue
        }
        # Name the backup after the run it came from (the pilot's runs\pilot-small model has the same hash).
        $label = 'previous'
        foreach ($candidate in (Get-ChildItem -Path (Join-Path $repo 'runs') -Recurse -Filter 'rfdetr_openimages.onnx' -File -ErrorAction SilentlyContinue)) {
            if ($candidate.Directory.Name -ne $Run -and (Get-FileHash $candidate.FullName).Hash -eq (Get-FileHash $installed).Hash) {
                $label = $candidate.Directory.Name; break
            }
        }
        $backup = Join-Path $target "rfdetr_openimages-$label.onnx"
        if (-not (Test-Path $backup)) {
            Copy-Item $installed $backup
            Write-Output "Kept the model that was installed as $backup"
        }
    }
    Copy-Item -Force $model.FullName $installed
    Write-Output "Installed $installed"
}
if ($unpacked) { Remove-Item -Recurse -Force $unpacked }   # the unpacked copy of the .zip
Write-Output 'Done. Open the app and pick the detector named RF-DETR ... Open Images (trained). Close the app before running this again.'
Write-Output 'To go back to the old model: copy the kept rfdetr_openimages-<name>.onnx over rfdetr_openimages.onnx.'
