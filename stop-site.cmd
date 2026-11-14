@echo off
setlocal
title MIR - stop
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-lan.ps1"
pause
endlocal
