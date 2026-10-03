[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskManifest=Get-Content -LiteralPath (Join-Path $taskRoot 'dependencies/windows-directml.json') -Raw | ConvertFrom-Json
$taskDeps=Join-Path $taskRoot '.deps'
$taskSdk=Join-Path $taskDeps $taskManifest.directory
New-Item -ItemType Directory -Path $taskDeps -Force | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach($taskPackage in $taskManifest.packages) {
    $taskArchive=Join-Path $taskDeps ($taskPackage.name+'.nupkg')
    if(-not(Test-Path -LiteralPath $taskArchive)) { Invoke-WebRequest $taskPackage.url -OutFile $taskArchive }
    if((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskPackage.sha256) { throw 'GPU dependency checksum mismatch; archive retained for inspection.' }
    $taskZip=[IO.Compression.ZipFile]::OpenRead($taskArchive)
    try {
        foreach($taskFile in $taskPackage.files.PSObject.Properties) {
            $taskEntry=$taskZip.GetEntry($taskFile.Name)
            if(-not $taskEntry) { throw "Missing GPU package entry: $($taskFile.Name)" }
            $taskTarget=Join-Path $taskSdk $taskFile.Value
            New-Item -ItemType Directory -Path (Split-Path -Parent $taskTarget) -Force | Out-Null
            [IO.Compression.ZipFileExtensions]::ExtractToFile($taskEntry,$taskTarget,$true)
        }
    } finally { $taskZip.Dispose() }
}
Write-Host "Optional native GPU runtime ready: $taskSdk. Rebuild to enable it. No system-wide installation was performed."
