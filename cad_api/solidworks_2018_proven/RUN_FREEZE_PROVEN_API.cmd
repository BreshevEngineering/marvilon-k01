@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\sw_api_proven_freeze_v1.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
