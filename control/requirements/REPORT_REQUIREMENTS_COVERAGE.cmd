@echo off
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0REPORT_REQUIREMENTS_COVERAGE.ps1"
pause
