@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON MEDTAS v8.4 - K01 Engineering Release Control Center
echo ================================================================================
echo Reliability mode:
echo   1. read-only API core self-test
echo   2. start local server only if API contract passes
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_K01_COMMAND_CENTER_SELFTEST.ps1"
set RC=%ERRORLEVEL%
if NOT %RC% EQU 0 (
  echo.
  echo COMMAND CENTER START BLOCKED: API core self-test failed.
  echo Fix the reported subsystem before starting the server.
  pause
  exit /b %RC%
)
echo.
echo API core self-test PASSED. Starting server...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0cc_server_v8.ps1"
set RC=%ERRORLEVEL%
if NOT %RC% EQU 0 pause
exit /b %RC%
