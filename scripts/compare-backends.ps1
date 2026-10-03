[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InputFile,
    [ValidateRange(20,1000000)][int]$Frames=120,
    [ValidateRange(0,100)][int]$Warmup=10,
    [string]$OutputDirectory
)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskInput=(Resolve-Path -LiteralPath $InputFile).Path
if(-not $OutputDirectory) { $OutputDirectory=Join-Path $taskRoot ('output/backend-comparison-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')) }
if(Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new comparison folder; existing results are never overwritten.' }
$taskOutput=(New-Item -ItemType Directory -Path $OutputDirectory).FullName
$taskComparisons=@()
foreach($taskModel in @('nano','small')) {
    foreach($taskBackend in @('cpu','directml')) {
        & (Join-Path $PSScriptRoot 'profile.ps1') -InputFile $taskInput -Frames $Frames -Warmup $Warmup -Model $taskModel -Backend $taskBackend -OutputDirectory (Join-Path $taskOutput "$taskModel-$taskBackend")
    }
    $taskCpu=Get-Content -LiteralPath (Join-Path $taskOutput "$taskModel-cpu/summary.json") -Raw | ConvertFrom-Json
    $taskGpu=Get-Content -LiteralPath (Join-Path $taskOutput "$taskModel-directml/summary.json") -Raw | ConvertFrom-Json
    if($taskGpu.backend -ne 'DirectML' -or $taskGpu.fallback -or $taskCpu.backend -ne 'CPU') { throw 'Comparison did not use the requested backend.' }
    if($taskCpu.input_sha256 -ne $taskGpu.input_sha256 -or $taskCpu.model_sha256 -ne $taskGpu.model_sha256 -or $taskCpu.executable_sha256 -ne $taskGpu.executable_sha256 -or $taskCpu.decoded_frames -ne $taskGpu.decoded_frames) { throw 'Comparison inputs/configuration changed.' }
    $taskComparisons += [ordered]@{
        model=$taskModel; measured_frames=$taskCpu.decoded_frames-$Warmup
        cpu_runtime=$taskCpu.runtime_version; gpu_runtime=$taskGpu.runtime_version; gpu_device=$taskGpu.device
        cpu_pipeline_ms=$taskCpu.stages_ms.pipeline_ms.mean; gpu_pipeline_ms=$taskGpu.stages_ms.pipeline_ms.mean
        cpu_effective_fps=1000/$taskCpu.stages_ms.pipeline_ms.mean; gpu_effective_fps=1000/$taskGpu.stages_ms.pipeline_ms.mean
        pipeline_speedup=$taskCpu.stages_ms.pipeline_ms.mean/$taskGpu.stages_ms.pipeline_ms.mean
        cpu_p95_ms=$taskCpu.stages_ms.pipeline_ms.p95; gpu_p95_ms=$taskGpu.stages_ms.pipeline_ms.p95
        cpu_peak_working_set_bytes=$taskCpu.observed_peak_working_set_bytes; gpu_peak_working_set_bytes=$taskGpu.observed_peak_working_set_bytes
        cpu_process_seconds=$taskCpu.process_wall_seconds; gpu_process_seconds=$taskGpu.process_wall_seconds
    }
}
[ordered]@{
    schema=1; created_utc=[DateTime]::UtcNow.ToString('o'); comparisons=$taskComparisons
    notes='Sequential native CLI on identical source/model/executable hashes. Warmup excluded from pipeline metrics; process time includes loading and warmup. CPU ORT 1.30.0 and isolated GPU ORT 1.24.4 differ, so this measures the shipped paths rather than isolating provider overhead. GPU Run includes transfers. No GUI/camera/accuracy claim; OS memory sampling does not measure VRAM. Results are local and are not uploaded.'
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskOutput 'comparison.json') -Encoding utf8
Write-Host "Backend comparison saved: $taskOutput"
