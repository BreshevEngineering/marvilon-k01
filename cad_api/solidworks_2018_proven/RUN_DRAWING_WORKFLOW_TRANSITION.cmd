@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\drawing_workflow_transition_v1.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
