@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 FEMM SCREENING INPUT PACK
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0BUILD_FEMM_SCREENING_INPUT_PACK.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
