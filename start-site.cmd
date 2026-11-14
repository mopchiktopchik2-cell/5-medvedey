@echo off
setlocal
title MIR - start
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-mir.ps1"
if errorlevel 1 (
    echo.
    pause
)
endlocal
