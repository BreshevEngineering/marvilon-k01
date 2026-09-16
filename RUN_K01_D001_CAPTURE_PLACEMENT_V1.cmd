@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\drawing_candidate_lifecycle_v1.py --repo-root "%CD%" capture --drawing-id K01-D-001
exit /b %ERRORLEVEL%
