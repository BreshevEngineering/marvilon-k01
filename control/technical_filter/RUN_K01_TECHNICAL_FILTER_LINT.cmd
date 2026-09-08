@echo off
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0K01_TECHNICAL_FILTER_LINT_v1.ps1"
pause
