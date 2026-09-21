@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\d006_import_all_dims_v2.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
