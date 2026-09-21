@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\d006_projection_compiler_v10.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
