@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\drawing_d3_verify_v15.py
exit /b %errorlevel%
