@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 C2 BOM PIPELINE
echo ================================================================================
call "RUN_K01_BOM.cmd" study
set RAWRC=%ERRORLEVEL%
echo.
echo Raw extractor exit code=%RAWRC%. Reconciliation will still run if the audit exists.
call "02_RECONCILE_K01_BOM_C2.cmd"
set RECRC=%ERRORLEVEL%
echo.
echo BOM pipeline complete. Raw=%RAWRC% Reconcile=%RECRC%
pause
if %RECRC% NEQ 0 exit /b %RECRC%
exit /b %RAWRC%
