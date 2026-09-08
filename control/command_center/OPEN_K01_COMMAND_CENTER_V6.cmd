@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 MEDTAS - Engineering Control Center v6
echo ================================================================================
echo Robust JSON API + active C2R1 design workflow. No Python required.
echo URL: http://127.0.0.1:8765/
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0cc_server_v6.ps1"
if errorlevel 1 (echo SERVER FAILED.&pause)
