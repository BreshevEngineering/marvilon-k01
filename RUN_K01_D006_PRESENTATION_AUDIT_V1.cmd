@echo off
setlocal
cd /d "%~dp0"
py -3 tools\medtas\drawing_presentation_audit_v1.py --repo-root "%CD%" --drawing-id K01-D-006 --spec control\drawings\spec\K01-D-006_P007_DRAWING_SPEC_v1.json
exit /b %ERRORLEVEL%
