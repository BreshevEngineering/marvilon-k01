@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MEDTAS K01 - COMMAND CENTER API CORE SELF-TEST
echo READ-ONLY: no CAD writes, no Git writes.
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_K01_COMMAND_CENTER_SELFTEST.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
