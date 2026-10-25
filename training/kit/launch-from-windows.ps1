# Work with the KIT cluster from the laptop in one command.
# Needs a working key-based SSH login (the Interactive key unlocked in the Windows agent).
# Run from the FrameTrail folder:
#   powershell -ExecutionPolicy Bypass -File training\kit\launch-from-windows.ps1 [-Action launch|resubmit|probe|status|sync|add|fetch]
# -Action add -Job smoke-model,full-data queues extra jobs next to the pilot chain; it never cancels anything.
# -Action fetch [-Run pilot-small] downloads a finished run's scores and app model into runs\ and models\.
param(
    [ValidateSet('launch', 'resubmit', 'probe', 'status', 'sync', 'add', 'fetch')][string]$Action = 'launch',
    [string]$Account = 'ka_udxvl@uc3.scc.kit.edu',
    [string]$Run = 'pilot-small',
    [string]$Job = ''
)
$ErrorActionPreference = 'Stop'
$training = Split-Path -Parent $PSScriptRoot
# A list arrives as one string through powershell -File, so split it here.
$jobs = @($Job -split '[,\s]+' | Where-Object { $_ })
foreach ($name in $jobs) {
    if ($name -notin @('full-data', 'smoke-model')) { throw "Unknown job '$name'. Jobs: full-data, smoke-model" }
}
if ($Action -eq 'add' -and $jobs.Count -eq 0) { throw 'Name the extra jobs, for example: -Action add -Job smoke-model,full-data' }

function Invoke-Checked([string]$what, [scriptblock]$command) {
    & $command
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" }
}

Invoke-Checked 'SSH login check' { ssh -o BatchMode=yes $Account 'echo connected to $(hostname)' }

if ($Action -eq 'fetch') {
    $repo = Split-Path -Parent $training
    $remote = (ssh -o BatchMode=yes $Account 'bash -lc ''echo $(ws_find frametrail)/rf/runs''' | Select-Object -Last 1)
    if ($LASTEXITCODE -ne 0 -or -not $remote -or $remote.Trim() -eq '/rf/runs') { throw 'Could not find the frametrail workspace' }
    $remote = $remote.Trim()
    ssh -o BatchMode=yes $Account "test -f $remote/$Run/eval-test.json -a -f $remote/$Run/rfdetr_openimages.onnx"
    if ($LASTEXITCODE -ne 0) {
        Write-Output "Run '$Run' has no test scores or app model yet. Check progress with -Action status."
        exit 1
    }
    $files = @("$Run/eval-test.json", "$Run/rfdetr_openimages.json", "$Run/rfdetr_openimages.onnx")
    # The baseline's scores on the same test split, when there are any (not for the smoke test).
    $baseline = "baseline-yolov8s-oiv7-$($Run.Split('-')[0])/eval-test.json"
    ssh -o BatchMode=yes $Account "test -f $remote/$baseline"
    if ($LASTEXITCODE -eq 0) { $files += $baseline }
    foreach ($file in $files) {
        $target = Join-Path $repo "runs\$($file.Replace('/', '\'))"
        New-Item -ItemType Directory -Force (Split-Path -Parent $target) | Out-Null
        Invoke-Checked "Fetching $file" { scp -q "${Account}:$remote/$file" $target }
    }
    # The app finds models in models\ next to its executable; build.ps1 copies models\ there too.
    $model = Join-Path $repo "runs\$Run\rfdetr_openimages.onnx"
    foreach ($folder in @((Join-Path $repo 'models'), (Join-Path $repo 'build\windows-msvc\Release\models'))) {
        if ($folder -like '*Release*' -and -not (Test-Path (Split-Path -Parent $folder))) { continue }
        New-Item -ItemType Directory -Force $folder | Out-Null
        Copy-Item -Force $model (Join-Path $folder 'rfdetr_openimages.onnx')
        Write-Output "Installed $folder\rfdetr_openimages.onnx"
    }
    if ($Run -eq 'gpu-smoke') {
        Write-Output 'This is the 2-epoch smoke-test model: use it to check that the app runs the profile on the GPU, not for accuracy.'
        Write-Output 'Fetching the real run later (-Action fetch) replaces it.'
    }
    return
}
# Shows which code is uploaded, so the output tells whether a git pull is missing.
$commit = git -C (Split-Path -Parent $training) log -1 --format='%h %s' 2>$null
if ($commit) { Write-Output "Uploading training code from commit $commit" }
Invoke-Checked 'Clearing the upload folder' { ssh -o BatchMode=yes $Account 'rm -rf ~/ft-training-new' }
Invoke-Checked 'Copying training/' { scp -q -r $training "${Account}:~/ft-training-new" }
# export.py maps trained classes onto the app's categories with this file.
$vocabulary = Join-Path (Split-Path -Parent $training) 'dependencies\recognition-vocabulary.json'
Invoke-Checked 'Copying the app vocabulary' { scp -q $vocabulary "${Account}:~/ft-training-new/recognition-vocabulary.json" }
Invoke-Checked "Remote '$Action'" { ssh -o BatchMode=yes $Account "bash -l ~/ft-training-new/kit/remote_launch.sh $Action $($jobs -join ' ')" }
