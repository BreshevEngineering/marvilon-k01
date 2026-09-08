@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 C2R1 BOM PIPELINE
echo ================================================================================
call "RUN_K01_BOM.cmd" r1
set RAWRC=%ERRORLEVEL%
echo.
echo Raw R1 extractor exit code=%RAWRC%.
echo Reconciliation remains C2 identity/material authority; quantities/path update only.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0K01_BOM_Reconcile.ps1" -Mode r1
set RECRC=%ERRORLEVEL%
echo.
pause
if %RECRC% NEQ 0 exit /b %RECRC%
exit /b %RAWRC%
