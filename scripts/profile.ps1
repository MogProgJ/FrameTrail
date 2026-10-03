[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InputFile,
    [ValidateRange(10, 1000000)][int]$Frames = 180,
    [ValidateRange(0, 100)][int]$Warmup = 5,
    [ValidateSet('nano','small','world-s','world-m','openimages')][string]$Model = 'nano',
    [ValidateSet('cpu','auto','directml')][string]$Backend = 'cpu',
    [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskInput = (Resolve-Path -LiteralPath $InputFile).Path
$taskManifestName=if($Model -in @('nano','small')){"yolox-$Model"}else{"yolo-$Model"}
$taskModelManifest = Get-Content (Join-Path $taskRoot "dependencies/$taskManifestName.json") -Raw | ConvertFrom-Json
$taskModel = Join-Path $taskRoot ('models/' + $taskModelManifest.filename)
$taskExe = Join-Path $taskRoot 'build/windows-msvc/Release/frametrail.exe'
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $taskRoot ('output/profile-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')) }
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new profile directory; existing results are never overwritten.' }
$taskOutput = (New-Item -ItemType Directory -Path $OutputDirectory).FullName
$taskCsv = Join-Path $taskOutput 'frames.csv'
$taskLog = Join-Path $taskOutput 'run.txt'
$taskErrors = Join-Path $taskOutput 'errors.txt'
# PowerShell Start-Process joins ArgumentList; quote paths and reject embedded quotes.
foreach ($taskPath in @($taskInput, $taskModel, $taskCsv)) {
    if ($taskPath.Contains('"')) { throw 'A path contains an unsupported quote.' }
}
$taskArguments = @('inspect', ('"' + $taskInput + '"'), '--detect', ('"' + $taskModel + '"'), '--model-type', $Model, '--backend', $Backend, '--track', '--profile', ('"' + $taskCsv + '"'), '--max-frames', "$Frames")
$taskWatch = [Diagnostics.Stopwatch]::StartNew()
$taskProcess = Start-Process -FilePath $taskExe -ArgumentList $taskArguments -PassThru -WindowStyle Hidden -RedirectStandardOutput $taskLog -RedirectStandardError $taskErrors
$taskPeak = 0L
do {
    try { $taskProcess.Refresh(); $taskPeak = [Math]::Max($taskPeak, $taskProcess.PeakWorkingSet64) } catch {}
    if (-not $taskProcess.HasExited) { Start-Sleep -Milliseconds 50 }
} while (-not $taskProcess.HasExited)
$taskProcess.WaitForExit(); $taskWatch.Stop()
if ($taskProcess.ExitCode -ne 0) { throw "Profile failed. See $taskErrors" }
$taskRows = @(Import-Csv -LiteralPath $taskCsv)
if ($taskRows.Count -le $Warmup) { throw 'Not enough decoded frames after the requested warmup exclusion.' }
$taskMeasured = @($taskRows | Select-Object -Skip $Warmup)
$taskStages = [ordered]@{}
foreach ($taskColumn in @('decode_rgb_ms','preprocess_ms','inference_ms','postprocess_ms','tracking_ms','pipeline_ms')) {
    $taskValues = @($taskMeasured | ForEach-Object { [double]::Parse($_.$taskColumn, [Globalization.CultureInfo]::InvariantCulture) } | Sort-Object)
    $taskStages[$taskColumn] = [ordered]@{
        mean = ($taskValues | Measure-Object -Average).Average
        p50 = $taskValues[[Math]::Max(0, [Math]::Ceiling($taskValues.Count * .50) - 1)]
        p95 = $taskValues[[Math]::Max(0, [Math]::Ceiling($taskValues.Count * .95) - 1)]
    }
}
$taskCpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$taskReport = [ordered]@{
    schema = 1; created_utc = [DateTime]::UtcNow.ToString('o')
    cpu = $taskCpu.Name; logical_processors = $taskCpu.NumberOfLogicalProcessors
    os = [Environment]::OSVersion.VersionString; requested_backend = $Backend
    backend = ((Get-Content -LiteralPath $taskLog | Where-Object { $_ -match '^Execution provider: ' }) -replace '^Execution provider: ','')
    runtime_version = ((Get-Content -LiteralPath $taskLog | Where-Object { $_ -match '^Runtime: ' }) -replace '^Runtime: ','')
    device = ((Get-Content -LiteralPath $taskLog | Where-Object { $_ -match '^Device: ' }) -replace '^Device: ','')
    fallback = ((Get-Content -LiteralPath $taskLog | Where-Object { $_ -match '^Fallback: ' }) -replace '^Fallback: ','')
    input_name = [IO.Path]::GetFileName($taskInput); input_sha256 = (Get-FileHash -LiteralPath $taskInput).Hash
    model_type = $Model
    model_sha256 = (Get-FileHash -LiteralPath $taskModel).Hash
    executable_sha256 = (Get-FileHash -LiteralPath $taskExe).Hash
    confidence = 0.35; nms_iou = 0.45; tracking_classes = @(0,1,2,3,5,7)
    counting_line = @(0.1,0.5,0.9,0.5); direction = 'both'
    frame_limit = $Frames; decoded_frames = $taskRows.Count; excluded_warmup_frames = $Warmup
    dimensions = @($taskRows | ForEach-Object { "$($_.width)x$($_.height)" } | Select-Object -Unique)
    observed_peak_working_set_bytes = $taskPeak; process_wall_seconds = $taskWatch.Elapsed.TotalSeconds
    stages_ms = $taskStages
    notes = 'File-based sequential CLI, no GUI or camera. Pipeline includes optional export work except the profile row itself. Decode includes RGB conversion/allocation. Inference includes tensor setup. Memory peak sampled from OS process counters; startup/exit may escape polling. No accuracy claim.'
}
$taskReport | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskOutput 'summary.json') -Encoding utf8
Write-Host "Profile saved: $taskOutput"
