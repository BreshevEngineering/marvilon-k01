@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
if "%~1"=="" (
  echo Usage: RUN_K01_ROTATIONAL_DRAWING_API.cmd ^<drawing-spec.json^>
  pause
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "cad_api\solidworks_2018_proven\rotational_family_v1\K01_ROTATIONAL_DRAWING_API.ps1" "%~1"
set RC=%ERRORLEVEL%
echo.
echo FINAL_RC=%RC%
pause
exit /b %RC%
