@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
if "%~1"=="" (
  echo Usage: RUN_K01_DRAWING_ANNOTATE_EXISTING_V1.cmd ^<job.json^>
  pause
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "cad_api\solidworks_2018_proven\drawing_annotate_existing_v1\K01_DRAWING_ANNOTATE_EXISTING_V1.ps1" "%~1"
set RC=%ERRORLEVEL%
echo.
echo FINAL_RC=%RC%
pause
exit /b %RC%
