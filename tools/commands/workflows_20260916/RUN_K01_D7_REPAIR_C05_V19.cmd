@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo [1/2] Remove the single unauthorized C05 display dimension from SAME K01-D-006 exemplar...
py -3 tools\medtas\drawing_d7_repair_c05_v19.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [2/2] Re-run D7 semantic QA on the same drawing...
call RUN_K01_D7_QA_D006_V15.cmd
exit /b %ERRORLEVEL%
