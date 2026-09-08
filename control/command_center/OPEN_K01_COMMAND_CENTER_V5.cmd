@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 MEDTAS - Engineering Control Center v5
echo ================================================================================
echo Task-driven local digital thread. No Python required.
echo URL: http://127.0.0.1:8765/
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0cc_server_v5.ps1"
if errorlevel 1 (echo SERVER FAILED.&pause)
