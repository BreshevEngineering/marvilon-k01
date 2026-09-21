@echo off
setlocal EnableExtensions
cd /d "D:\BreshevEngineering\marvilon-k01"
if "%~1"=="" (
  echo Usage: RUN_DRAWING_SYSTEM_PRODUCTION.cmd ^<contract.json^> [output_dir]
  pause
  exit /b 2
)
set "CONTRACT=%~1"
set "OUT=%~2"
if "%OUT%"=="" set "OUT=reports\cad\drawing_system_v5\result_current"
if not exist "%OUT%" mkdir "%OUT%"
set "LOG=%OUT%\RUN_LAST.log"
set "PYTHONPATH=%CD%\tools\medtas;%PYTHONPATH%"
echo ============================================================ > "%LOG%"
echo MARVILON DRAWING SYSTEM V5.2.2 SELF-CONTAINED >> "%LOG%"
echo HOLD BLOCKS RELEASE, NOT RESULT GENERATION >> "%LOG%"
echo ============================================================ >> "%LOG%"
py -3 -m drawing_system_v5.result_runner --repo-root "%CD%" --contract "%CONTRACT%" --mode manufacturing --outdir "%OUT%" --native >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
type "%LOG%"
echo.
echo RUN_LOG=%CD%\%LOG%
echo RESULT_JSON=%CD%\%OUT%\RESULT_CURRENT.json
echo FINAL_RC=%RC%
echo.
pause
exit /b %RC%
