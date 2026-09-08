@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.2 - 37_AUDIT_PROJECT_STRUCTURE
echo ============================================================
py -3 tools\medtas\project_structure_audit_v2_2.py --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
