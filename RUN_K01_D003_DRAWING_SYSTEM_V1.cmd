@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\drawing_system_v1.py --repo-root "%CD%" --spec control\drawings\spec\K01-D-003_P003_DRAWING_SPEC_v2.json --mode review
exit /b %ERRORLEVEL%
