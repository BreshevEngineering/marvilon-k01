@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\d004_iso_exemplar_v1.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
