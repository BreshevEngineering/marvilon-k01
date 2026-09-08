@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 BOM - RECONCILE CAD QUANTITIES WITH CONTROLLED IDENTITY/MATERIAL STATUS
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0K01_BOM_Reconcile.ps1"
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
