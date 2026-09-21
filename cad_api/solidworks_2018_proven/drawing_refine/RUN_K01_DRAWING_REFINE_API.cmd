@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: %~nx0 ^<job.json^>
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0K01_DRAWING_REFINE_API.ps1" "%~1"
set "RC=%ERRORLEVEL%"
echo.
echo RC=%RC%
pause
exit /b %RC%
