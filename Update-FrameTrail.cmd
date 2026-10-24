@echo off
rem Double-click after FrameTrail updates: gets the new code, rebuilds only the app, refreshes the
rem desktop and Start menu shortcuts, and opens FrameTrail.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update.ps1"
if errorlevel 1 (
    echo.
    echo The update did not finish. The message above says why.
    pause
)
