@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\drawing_presentation_audit_v1.py --repo-root "%CD%" --drawing-id K01-D-003 --spec control\drawings\spec\K01-D-003_P003_DRAWING_SPEC_v2.json
exit /b %ERRORLEVEL%
