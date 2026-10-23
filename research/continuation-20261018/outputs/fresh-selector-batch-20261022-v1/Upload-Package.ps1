$ErrorActionPreference='Stop'
function Get-FrameTrailSha256([string]$Path) {
  $taskStream=[System.IO.File]::OpenRead($Path);$taskSha=[System.Security.Cryptography.SHA256]::Create()
  try { return ([System.BitConverter]::ToString($taskSha.ComputeHash($taskStream))).Replace('-','').ToLowerInvariant() }
  finally { $taskSha.Dispose();$taskStream.Dispose() }
}
$taskReceipt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'archive-receipt.json') | ConvertFrom-Json
$taskArchive=Join-Path $PSScriptRoot $taskReceipt.archive
$taskStart=Join-Path $PSScriptRoot $taskReceipt.cluster_start_script
if ((Get-FrameTrailSha256 $taskArchive) -ne $taskReceipt.archive_sha256 -or (Get-FrameTrailSha256 $taskStart) -ne $taskReceipt.cluster_start_script_sha256) { throw 'Sealed package/start script differs. No upload.' }
$taskTests=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'PACKAGE_TEST_REPORT.json') | ConvertFrom-Json
if ($taskTests.status -ne 'passed' -or $taskTests.package_seal_sha256 -ne $taskReceipt.package_seal_sha256) { throw 'Tested package receipt missing or mismatched.' }
Write-Host 'Uploading the two-trial package only. Enter KIT OTP/password directly when SCP asks.'
& scp -o StrictHostKeyChecking=yes $taskArchive $taskStart 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
if ($LASTEXITCODE -ne 0) { throw 'Upload stopped. This helper does not submit jobs.' }
Write-Host ('In your existing cluster terminal: bash '+[char]34+'$(ws_find frametrail)/FrameTrail/output/'+$taskReceipt.cluster_start_script+[char]34)
