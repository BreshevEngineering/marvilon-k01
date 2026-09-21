@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\d006_professional_candidate_current_v1.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
