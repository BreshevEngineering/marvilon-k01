@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
 echo Usage: 30_INGEST_INSPECTION_RESULTS.cmd path-to-results.csv
 pause
 exit /b 2
)
py -3 tools\medtas\ingest_inspection_results_v1_9.py --repo-root "%CD%" --results "%~1"
pause
