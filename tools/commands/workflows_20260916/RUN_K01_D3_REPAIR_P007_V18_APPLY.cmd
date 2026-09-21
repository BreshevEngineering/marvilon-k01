@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo [1/2] Apply controlled C01 + annotation-view repair to SAME V12 exemplar...
py -3 tools\medtas\drawing_d3_repair_v18.py --mode apply
if errorlevel 1 exit /b %ERRORLEVEL%

echo [2/2] Re-run contract-driven D3 and refresh MEDTAS / handoff / coherence...
call RUN_K01_D3_VERIFY_P007_V17.cmd
exit /b %ERRORLEVEL%
