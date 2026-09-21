@echo off
setlocal
set "DRAWING=D:\Marvilon\K01\cad\drawings\candidates\K01-D-005\drawing_system_v1_20260920_225023\generated\K01-D-005.SLDDRW"
if not exist "%DRAWING%" (
  echo STATUS=HOLD_KNOWN_D005_DRAWING_NOT_FOUND
  echo EXPECTED=%DRAWING%
  pause
  exit /b 3
)
cd /d "D:\BreshevEngineering\marvilon-k01"
powershell -NoProfile -ExecutionPolicy Bypass -File "cad_api\solidworks_2018_proven\drawing_qa\native_attachment_v1\K01_DRAWING_NATIVE_ATTACHMENT_QA.ps1" --inventory "%DRAWING%"
set RC=%ERRORLEVEL%
echo.
echo FINAL_RC=%RC%
pause
exit /b %RC%
