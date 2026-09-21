@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
if "%~1"=="" (
  echo Usage: RUN_K01_DRAWING_NATIVE_ATTACHMENT_INVENTORY.cmd ^<drawing.slddrw^>
  pause
  exit /b 2
)
powershell -NoProfile -ExecutionPolicy Bypass -File "cad_api\solidworks_2018_proven\drawing_qa\native_attachment_v1\K01_DRAWING_NATIVE_ATTACHMENT_QA.ps1" --inventory "%~1"
set RC=%ERRORLEVEL%
echo.
echo FINAL_RC=%RC%
pause
exit /b %RC%
