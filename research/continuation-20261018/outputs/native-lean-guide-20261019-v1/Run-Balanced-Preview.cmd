@echo off
setlocal
if not exist "%~dp0optional\models\rfdetr_balanced7805570_step100.onnx" if not exist "%~dp0app\models\rfdetr_balanced7805570_step100.onnx" (
  echo The balanced preview needs the optional RF model pack next to the app folder.
  exit /b 2
)
start "" "%~dp0app\frametrail-desktop.exe" --rf-balanced %*
