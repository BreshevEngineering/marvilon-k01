@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\d006_exemplar_capture_v12.py
exit /b %errorlevel%
