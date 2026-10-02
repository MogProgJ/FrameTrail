function Find-FrameTrailCMake {
    $taskCommand = Get-Command cmake -ErrorAction SilentlyContinue
    if ($taskCommand) { return $taskCommand.Source }
    $taskVswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (Test-Path -LiteralPath $taskVswhere) {
        $taskCandidates = @(& $taskVswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.CMake.Project -find '**/cmake.exe')
        if ($taskCandidates.Count -gt 0) { return $taskCandidates[0] }
    }
    throw 'CMake not found. Install Visual Studio 2022 Desktop development with C++ (including CMake), or add CMake 3.25+ to PATH.'
}
