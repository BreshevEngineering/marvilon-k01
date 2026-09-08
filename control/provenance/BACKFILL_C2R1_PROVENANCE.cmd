@echo off
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0BACKFILL_C2R1_PROVENANCE.ps1"
pause
