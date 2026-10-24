# Copy training/ to the KIT cluster and start the pilot, from the laptop in one command.
# Needs a working key-based SSH login (the Interactive key unlocked in the Windows agent).
# Run from the FrameTrail folder:  powershell -ExecutionPolicy Bypass -File training\kit\launch-from-windows.ps1
param([string]$Account = 'ka_udxvl@uc3.scc.kit.edu')
$ErrorActionPreference = 'Stop'
$training = Split-Path -Parent $PSScriptRoot

function Invoke-Checked([string]$what, [scriptblock]$command) {
    & $command
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" }
}

Invoke-Checked 'SSH login check' { ssh -o BatchMode=yes $Account 'echo connected to $(hostname)' }
Invoke-Checked 'Clearing the upload folder' { ssh -o BatchMode=yes $Account 'rm -rf ~/ft-training-new' }
Invoke-Checked 'Copying training/' { scp -q -r $training "${Account}:~/ft-training-new" }
Invoke-Checked 'Remote setup and submission' { ssh -o BatchMode=yes $Account 'bash -l ~/ft-training-new/kit/remote_launch.sh' }
Write-Host 'Pilot submitted. Job IDs are in logs/submitted.txt in the cluster workspace (rf folder).'
