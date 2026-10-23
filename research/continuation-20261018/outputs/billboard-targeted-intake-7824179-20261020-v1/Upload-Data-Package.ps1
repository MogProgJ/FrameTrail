$ErrorActionPreference='Stop'
function Get-FrameTrailSha256([string]$Path) {
    $taskStream=[System.IO.File]::OpenRead($Path)
    $taskSha=[System.Security.Cryptography.SHA256]::Create()
    try { return ([System.BitConverter]::ToString($taskSha.ComputeHash($taskStream))).Replace('-','').ToLowerInvariant() }
    finally { $taskSha.Dispose(); $taskStream.Dispose() }
}
$taskReceipt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'archive-receipt.json') | ConvertFrom-Json
$taskPath=Join-Path $PSScriptRoot $taskReceipt.archive
if ((Get-FrameTrailSha256 $taskPath) -ne $taskReceipt.archive_sha256) { throw 'Package checksum differs; no upload.' }
$taskStart=Join-Path $PSScriptRoot $taskReceipt.cluster_start_script
if ((Get-FrameTrailSha256 $taskStart) -ne $taskReceipt.cluster_start_script_sha256) { throw 'Start script checksum differs; no upload.' }
Write-Host 'Upload only. Enter KIT OTP/password directly. Submit using your existing cluster session afterward.'
& scp -o StrictHostKeyChecking=yes $taskPath $taskStart 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
if ($LASTEXITCODE -ne 0) { throw 'Upload stopped; preserve output. No job was submitted by this helper.' }
Write-Host ('Upload finished. In your existing cluster terminal: bash '+[char]34+'$(ws_find frametrail)/FrameTrail/output/'+$taskReceipt.cluster_start_script+[char]34)
