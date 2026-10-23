param([switch]$Configure)
$ErrorActionPreference = 'Stop'
$taskBase = $PSScriptRoot
$taskCmake = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
$taskProject = 'C:/Users/nazee/Documents/All Modules/FrameTrail'
if ($Configure) {
  & $taskCmake -S (Join-Path $taskBase 'source') -B (Join-Path $taskBase 'build') -G 'Visual Studio 17 2022' -A x64 "-DFFMPEG_ROOT=$taskProject/.deps/ffmpeg-n8.1.3-9-g29e619e767-win64-lgpl-shared-8.1" "-DONNXRUNTIME_ROOT=$taskProject/.deps/onnxruntime-win-x64-1.30.0" "-DSQLITE_ROOT=$taskProject/.deps/sqlite-amalgamation-3530400" "-DFRAMETRAIL_QT_ROOT=$taskProject/.deps/qt-6.11.3-msvc2022-x64" "-DFRAMETRAIL_DIRECTML_ROOT=$taskProject/.deps/directml-ort-1.24.4" "-DFRAMETRAIL_MODEL_ROOT=$taskProject/models" "-DFRAMETRAIL_RF_MODEL=$taskProject/models/rfdetr_scale7758628.onnx"
  if ($LASTEXITCODE -ne 0) { throw 'Configuration failed' }
}
& $taskCmake --build (Join-Path $taskBase 'build') --config Release --parallel 2 --target frametrail-desktop frametrail_cached_playback_tests frametrail_preview_tests frametrail_desktop_tests frametrail_saved_desktop_tests
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
