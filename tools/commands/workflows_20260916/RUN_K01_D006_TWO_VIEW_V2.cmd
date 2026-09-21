@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\d006_two_view_v2.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
