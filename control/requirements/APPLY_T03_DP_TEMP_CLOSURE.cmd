@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0APPLY_T03_DP_TEMP_CLOSURE.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
