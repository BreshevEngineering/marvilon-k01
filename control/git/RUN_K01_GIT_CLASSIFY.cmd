@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 GIT CLASSIFICATION - READ ONLY - NO STAGE / NO COMMIT
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0K01_GIT_CLASSIFY.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
