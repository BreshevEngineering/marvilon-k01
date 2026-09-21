@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
if "%~1"=="" (
  echo Usage: RUN_DRAWING_SYSTEM_V5_RESULT.cmd ^<contract.json^> [review^|manufacturing] [output_dir] [native]
  exit /b 2
)
set CONTRACT=%~1
set MODE=%~2
if "%MODE%"=="" set MODE=manufacturing
set OUT=%~3
if "%OUT%"=="" set OUT=reports\cad\drawing_system_v5\result_current
set NATIVE=%~4
set PYTHONPATH=%CD%\tools\medtas;%PYTHONPATH%
if /I "%NATIVE%"=="native" (
  py -3 -m drawing_system_v5.result_runner --repo-root "%CD%" --contract "%CONTRACT%" --mode "%MODE%" --outdir "%OUT%" --native
) else (
  py -3 -m drawing_system_v5.result_runner --repo-root "%CD%" --contract "%CONTRACT%" --mode "%MODE%" --outdir "%OUT%"
)
set RC=%ERRORLEVEL%
echo FINAL_RC=%RC%
exit /b %RC%
