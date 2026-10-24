@echo off
rem Opens FrameTrail at once. It only builds the app first if it has never been built.
rem After FrameTrail updates, use Update-FrameTrail.cmd instead.
set "APP=%~dp0build\windows-msvc\Release\frametrail-desktop.exe"
if not exist "%APP%" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build.ps1" -AppOnly
    if errorlevel 1 ( pause & exit /b 1 )
)
start "" "%APP%" %*
