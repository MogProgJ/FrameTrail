[CmdletBinding()]
param(
    # Video files, or a folder of them. Short clips are best (the whole video is analysed, up to -MaxFrames).
    [Parameter(Mandatory)][string[]]$Videos,
    # More trained RF-DETR Open Images models to try, as name=path (for example round3=C:\models\rfdetr_openimages-round3.onnx).
    [string[]]$Models=@(),
    [ValidateRange(0.05,0.95)][double]$Confidence=0.35,
    [ValidateRange(0.05,0.95)][double]$ReferenceScore=0.5,
    [ValidateRange(1,100000)][int]$MaxFrames=300,
    [ValidateSet('cpu','auto')][string]$Backend='auto',
    [string]$OutputDirectory
)
# How much of what YOLOX-S confidently sees on your own videos does each model also find? See training/footage_check.py.
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$cli=Join-Path $root 'build/windows-msvc/Release/frametrail.exe'
if(-not (Test-Path -LiteralPath $cli)) { throw "Build FrameTrail first (scripts\build.ps1): $cli is missing." }
$modelDir=Join-Path $root 'models'
$yolox=Join-Path $modelDir 'yolox_s.onnx'
$trained=Join-Path $modelDir 'rfdetr_openimages.onnx'
foreach($file in @($yolox,$trained)) { if(-not (Test-Path -LiteralPath $file)) { throw "Missing model: $file" } }
$files=@()
foreach($item in $Videos) {
    if(Test-Path -LiteralPath $item -PathType Container) { $files+=Get-ChildItem -LiteralPath $item -File | Where-Object { $_.Extension -in '.mp4','.mkv','.mov','.avi','.webm' } }
    else { $files+=Get-Item -LiteralPath $item }
}
if(-not $files) { throw 'No videos found.' }
if(-not $OutputDirectory) { $OutputDirectory=Join-Path $root ('output/footage-check-'+(Get-Date -Format 'yyyyMMdd-HHmmss')) }
if(Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new output folder; existing results are never overwritten.' }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
# Which videos, in order (01, 02, ...), so the same check can be repeated on a new model.
$files | ForEach-Object { $_.FullName } | Set-Content -LiteralPath (Join-Path $OutputDirectory 'videos.txt') -Encoding utf8

# Candidates: name -> inspect arguments. Reference: YOLOX-S itself.
$candidates=[ordered]@{
    'trained'=@('--detect',$trained,'--model-type','rfdetr-oi')
    'combined'=@('--detect',$trained,'--model-type','rfdetr-oi','--combine',$yolox)
}
foreach($spec in $Models) {
    $name,$path=$spec -split '=',2
    if(-not $path -or -not (Test-Path -LiteralPath $path)) { throw "Use -Models name=path to an existing .onnx file (got '$spec')." }
    $candidates[$name]=@('--detect',(Resolve-Path -LiteralPath $path).Path,'--model-type','rfdetr-oi')
}
function Invoke-Detections($video,$csv,$arguments) {
    & $cli inspect $video.FullName @arguments --backend $Backend --confidence $Confidence --max-frames $MaxFrames --detections $csv 2>&1 | Out-Null
    if($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $csv)) { throw "Detection failed for $($video.Name): $($arguments -join ' ')" }
}
$reference=@(); $perCandidate=@{}; foreach($name in $candidates.Keys) { $perCandidate[$name]=@() }
$index=0
foreach($video in $files) {
    $index++; $prefix='{0:00}' -f $index
    Write-Host "[$index/$($files.Count)] $($video.Name)"
    $csv=Join-Path $OutputDirectory "$prefix-yolox.csv"
    Invoke-Detections $video $csv @('--detect',$yolox,'--model-type','small'); $reference+=$csv
    foreach($name in $candidates.Keys) {
        $csv=Join-Path $OutputDirectory "$prefix-$name.csv"
        Invoke-Detections $video $csv $candidates[$name]; $perCandidate[$name]+=$csv
    }
}
$python=(Get-Command python -ErrorAction Stop).Source
$arguments=@((Join-Path $root 'training/footage_check.py'),'--reference')+$reference+@('--ref-score',$ReferenceScore,'--cand-score',$Confidence)
foreach($name in $candidates.Keys) { $arguments+=@('--candidate',"$name=$($perCandidate[$name] -join ',')") }
$arguments+=@('--out',(Join-Path $OutputDirectory 'report.md'))
& $python @arguments
Write-Host "`nSaved to $OutputDirectory"
