@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\d006_refine_existing_current_v1.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
