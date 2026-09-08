@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 MEDTAS - STABLE CORE PREFLIGHT
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0control\system\PREFLIGHT.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
