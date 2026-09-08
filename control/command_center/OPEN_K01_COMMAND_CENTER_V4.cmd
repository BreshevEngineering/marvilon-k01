@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 MEDTAS - Engineering Control Center v4
echo ================================================================================
echo Local-only server on 127.0.0.1:8765. Python is not required.
echo Reads reports, CAD artifacts, BOM and local Git status.
echo Write-capable actions run only after an explicit button click.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0cc_server_v4.ps1"
if errorlevel 1 (echo SERVER FAILED.&pause)
