@echo off
setlocal EnableExtensions
cd /d "D:\BreshevEngineering\marvilon-k01"
set "OUT=reports\cad\drawing_system_simple\K01-D-005\current"
if not exist "%OUT%" mkdir "%OUT%"
set "LOG=%OUT%\RUN_LAST.log"
echo ============================================================ > "%LOG%"
echo K01 DRAWING SYSTEM SIMPLE V1 >> "%LOG%"
echo CONTRACT -> LEGACY SPEC -> SOLIDWORKS -> RESULT >> "%LOG%"
echo ============================================================ >> "%LOG%"
py -3 tools\medtas\drawing_system_simple_v1.py --repo-root "%CD%" --contract control\drawings\contracts\K01-D-005_DRAWING_CONTRACT_v2_1.json --outdir "%OUT%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
type "%LOG%"
echo.
echo RUN_LOG=%CD%\%LOG%
echo RESULT_JSON=%CD%\%OUT%\RESULT_CURRENT.json
echo FINAL_RC=%RC%
pause
exit /b %RC%
