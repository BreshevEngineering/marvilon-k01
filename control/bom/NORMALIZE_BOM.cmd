@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 BOM NORMALIZATION - READ ONLY PRODUCT DATA REVIEW
echo ================================================================================
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0NORMALIZE_BOM.ps1"
set RC=%ERRORLEVEL%
pause
exit /b %RC%
