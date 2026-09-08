@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON MEDTAS - K01
echo Stable command-center filenames. Git is the version history.
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\..\tests\run_core_tests.ps1"
if errorlevel 1 (
 echo CORE TESTS FAILED. Server start blocked.
 pause
 exit /b 2
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0server.ps1"
