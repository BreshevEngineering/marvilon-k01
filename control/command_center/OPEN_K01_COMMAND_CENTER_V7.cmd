@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 MEDTAS - Engineering Control Center v7
echo ================================================================================
echo Evidence-reduced task state + event ledger + in-center engineering dossier.
echo No Python required. Local-only: http://127.0.0.1:8765/
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0cc_server_v7.ps1"
if errorlevel 1 (echo SERVER FAILED.&pause)
