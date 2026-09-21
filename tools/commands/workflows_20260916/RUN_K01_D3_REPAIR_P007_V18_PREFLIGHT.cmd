@echo off
setlocal
cd /d "%~dp0\..\..\.."
echo [V18 PRECHECK] Controlled repair preflight for SAME V12 P007 exemplar...
py -3 tools\medtas\drawing_d3_repair_v18.py --mode preflight
exit /b %ERRORLEVEL%
