@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 MEDTAS v8.3 - READ-ONLY PREFLIGHT
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0control\system\K01_MEDTAS_V8_PREFLIGHT.ps1"
set RC=%ERRORLEVEL%
echo.
if %RC% EQU 0 echo PREFLIGHT PASSED.
if NOT %RC% EQU 0 echo PREFLIGHT HOLD. Read the report before running engineering actions.
pause
exit /b %RC%
