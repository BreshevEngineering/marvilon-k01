@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\d006_base_drawing_v7.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
