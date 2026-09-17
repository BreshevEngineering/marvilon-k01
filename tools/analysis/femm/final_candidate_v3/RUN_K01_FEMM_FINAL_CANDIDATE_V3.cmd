@echo off
setlocal EnableExtensions
set "REPO=D:\BreshevEngineering\marvilon-k01"
set "OUT=%REPO%\reports\femm\final_candidate_20260916_v3"
if not exist "%OUT%" mkdir "%OUT%"

set "FEMM=C:\femm42\bin\femm.exe"
if not exist "%FEMM%" set "FEMM=C:\Program Files\femm42\bin\femm.exe"
if not exist "%FEMM%" set "FEMM=C:\Program Files\FEMM 4.2\bin\femm.exe"
if not exist "%FEMM%" set "FEMM=C:\Program Files (x86)\femm42\bin\femm.exe"
if not exist "%FEMM%" (
  echo ERROR: FEMM 4.2 not found.
  pause
  exit /b 2
)

set "HERE=%~dp0"
echo ============================================================
echo K01 FEMM V3 - FINAL CANDIDATE
echo ============================================================
echo FEMM: %FEMM%
echo SCRIPT: %HERE%K01_FEMM_FINAL_CANDIDATE_V3.lua
echo OUTPUT: %OUT%
echo.

del /q "%OUT%\K01_FEMM_SWEEP_V3_PASS.txt" 2>nul
"%FEMM%" -lua-script="%HERE%K01_FEMM_FINAL_CANDIDATE_V3.lua" -windowhide

if not exist "%OUT%\K01_FEMM_SWEEP_V3_PASS.txt" (
  echo.
  echo HOLD: V3 FEMM did not create PASS marker.
  echo LOG: %OUT%\K01_FEMM_FINAL_CANDIDATE_V3.log
  pause
  exit /b 3
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%HERE%POSTPROCESS_K01_FEMM_FINAL_CANDIDATE_V3.py"
) else (
  python "%HERE%POSTPROCESS_K01_FEMM_FINAL_CANDIDATE_V3.py"
)
if errorlevel 1 (
  echo POSTPROCESS HOLD
  pause
  exit /b %ERRORLEVEL%
)

echo.
echo PASS: FEMM V3 completed.
echo The window will stay open for review.
echo.
pause
endlocal
