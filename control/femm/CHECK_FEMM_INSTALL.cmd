@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 FEMM SOLVER FINGERPRINT - READ ONLY
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0CHECK_FEMM_INSTALL.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
