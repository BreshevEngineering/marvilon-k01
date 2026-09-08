@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 MEDTAS - Engineering Control Center v3
echo ================================================================================
echo PowerShell local server. Python is NOT required.
echo It does not modify CAD or Git.
echo Close this window to stop the server.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0cc_server.ps1"
if errorlevel 1 (
  echo.
  echo SERVER FAILED.
  echo Return the complete console output.
  pause
)
