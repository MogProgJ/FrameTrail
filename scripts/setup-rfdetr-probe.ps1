param([Parameter(Mandatory=$true)][string]$Python)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$taskEnvironment = Join-Path $taskProjectRoot '.deps\rfdetr-probe-cpu'
$taskMarker = Join-Path $taskEnvironment 'frametrail-probe-environment.json'
$taskRequirements = Join-Path $PSScriptRoot 'requirements-rfdetr-probe.txt'
$taskRequirementsHash = (Get-FileHash -LiteralPath $taskRequirements -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'Pass the full path to a Python 3.12 executable.' }
$taskVersion = & $Python -B -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
if ($LASTEXITCODE -ne 0 -or $taskVersion.Trim() -ne '3.12') { throw 'This probe is pinned to Python 3.12.' }
if (Test-Path -LiteralPath $taskEnvironment) {
    if (-not (Test-Path -LiteralPath $taskMarker -PathType Leaf)) { throw 'Existing unmarked environment is preserved. Choose a different environment; do not overwrite it.' }
    $taskExisting = Get-Content -LiteralPath $taskMarker -Raw | ConvertFrom-Json
    if ($taskExisting.purpose -ne 'rfdetr-small-cpu-probe-only' -or $taskExisting.requirements_sha256 -ne $taskRequirementsHash) {
        throw 'Existing environment belongs to another configuration and is preserved.'
    }
} else {
    & $Python -m venv $taskEnvironment
    if ($LASTEXITCODE -ne 0) { throw 'Isolated environment creation failed.' }
    @{schema=1;purpose='rfdetr-small-cpu-probe-only';requirements_sha256=$taskRequirementsHash;created_at_utc=[DateTime]::UtcNow.ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath $taskMarker -Encoding utf8
}
$taskProbePython = Join-Path $taskEnvironment 'Scripts\python.exe'
$taskInstallReport = Join-Path $taskEnvironment 'pip-install-report.json'
$taskFreeze = Join-Path $taskEnvironment 'installed-packages.txt'
if ((Test-Path -LiteralPath $taskInstallReport -PathType Leaf) -and (Test-Path -LiteralPath $taskFreeze -PathType Leaf)) {
    # A no-op pip rerun would replace the wheel receipt with an empty install list.
    & $taskProbePython -B -c 'import sys; sys.path.insert(0,sys.argv[1]); from rfdetr_probe import package_versions; print(package_versions())' $PSScriptRoot
    if ($LASTEXITCODE -ne 0) { throw 'Existing environment failed verification; its receipts are preserved. Inspect before reinstalling.' }
    & $taskProbePython -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Existing environment dependency consistency check failed.' }
    Write-Output "Reusing verified probe Python: $taskProbePython"
    return
}
& $taskProbePython -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --index-url https://download.pytorch.org/whl/cpu 'torch==2.8.0+cpu' 'torchvision==0.23.0+cpu'
if ($LASTEXITCODE -ne 0) { throw 'CPU wheel installation failed; the marked partial environment is preserved for a safe retry.' }
& $taskProbePython -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --index-url https://pypi.org/simple -r $taskRequirements --report (Join-Path $taskEnvironment 'pip-install-report.json')
if ($LASTEXITCODE -ne 0) { throw 'RF-DETR installation failed; preserve the partial environment and inspect the error.' }
& $taskProbePython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency consistency check failed.' }
& $taskProbePython -m pip freeze | Set-Content -LiteralPath (Join-Path $taskEnvironment 'installed-packages.txt') -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'Environment snapshot failed.' }
Write-Output "Probe Python: $taskProbePython"
Write-Output 'No training, camera activation, model adoption or desktop changes performed.'
