$ErrorActionPreference='Stop'
$taskFolder=$PSScriptRoot
$taskFixture=Join-Path $taskFolder ('test-fixtures\powershell-'+[guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $taskFixture | Out-Null
foreach ($taskName in 'Upload-Package.ps1','Retrieve-And-Evaluate.ps1') {
  $taskTokens=$null;$taskErrors=$null
  [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $taskFolder $taskName),[ref]$taskTokens,[ref]$taskErrors) | Out-Null
  if ($taskErrors.Count -gt 0) { throw ($taskErrors | Out-String) }
}
Copy-Item -LiteralPath (Join-Path $taskFolder 'Upload-Package.ps1') -Destination $taskFixture
[IO.File]::WriteAllText((Join-Path $taskFixture 'tiny.tar.gz'),'test archive')
[IO.File]::WriteAllText((Join-Path $taskFixture 'start.sh'),'literal sha256sum $1 0123456789')
function Get-TestSha([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
@{archive='tiny.tar.gz';archive_sha256=(Get-TestSha (Join-Path $taskFixture 'tiny.tar.gz'));cluster_start_script='start.sh';cluster_start_script_sha256=(Get-TestSha (Join-Path $taskFixture 'start.sh'));package_seal_sha256='mockseal'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskFixture 'archive-receipt.json')
@{status='passed';package_seal_sha256='mockseal'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskFixture 'PACKAGE_TEST_REPORT.json')
$global:FrameTrailMockScpCalls=0
$global:FrameTrailMockScpArgs=@()
function global:scp { $global:FrameTrailMockScpCalls++;$global:FrameTrailMockScpArgs=@($args);$global:LASTEXITCODE=0 }
& (Join-Path $taskFixture 'Upload-Package.ps1')
if ($global:FrameTrailMockScpCalls -ne 1 -or $global:FrameTrailMockScpArgs.Count -ne 5) { throw 'Expected one SCP with exactly archive+start+destination and two host-key options.' }
if ($global:FrameTrailMockScpArgs[1] -ne 'StrictHostKeyChecking=yes') { throw 'Host-key check lost.' }
[IO.File]::AppendAllText((Join-Path $taskFixture 'tiny.tar.gz'),'tamper')
$taskBlocked=$false
try { & (Join-Path $taskFixture 'Upload-Package.ps1') } catch { $taskBlocked=$true }
if (-not $taskBlocked -or $global:FrameTrailMockScpCalls -ne 1) { throw 'Tampered archive was not blocked before SCP.' }
Remove-Item Function:\scp
@{status='passed';powershell_parser_errors=0;mock_upload_connections=1;archive_and_start_uploaded_together=$true;tampered_package_blocked=$true;real_network_calls=0} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskFolder 'POWERSHELL_TEST_REPORT.json')
Get-Content -LiteralPath (Join-Path $taskFolder 'POWERSHELL_TEST_REPORT.json')
