@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\d006_automated_native_pmi_v6.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
