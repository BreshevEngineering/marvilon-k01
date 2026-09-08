@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 GITHUB REMOTE HEALTH - READ ONLY
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK_K01_GITHUB_REMOTE.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
