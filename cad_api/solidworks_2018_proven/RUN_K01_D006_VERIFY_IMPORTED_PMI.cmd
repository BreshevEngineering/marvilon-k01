@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\d006_verify_imported_pmi_current_v1.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
