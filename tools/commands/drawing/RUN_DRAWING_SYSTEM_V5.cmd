@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
if "%~1"=="" (
  echo Usage: RUN_DRAWING_SYSTEM_V5.cmd ^<contract.json^> [review^|manufacturing] [output_dir]
  exit /b 2
)
set CONTRACT=%~1
set MODE=%~2
if "%MODE%"=="" set MODE=review
set OUT=%~3
if "%OUT%"=="" set OUT=reports\cad\drawing_system_v5\current
set PYTHONPATH=%CD%\tools\medtas\drawing_system_v5;%PYTHONPATH%
py -3 -m drawing_system_v5.cli pipeline --contract "%CONTRACT%" --mode "%MODE%" --outdir "%OUT%"
set RC=%ERRORLEVEL%
echo FINAL_RC=%RC%
exit /b %RC%
