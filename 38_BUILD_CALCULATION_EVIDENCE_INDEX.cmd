@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.2 - 38_BUILD_CALCULATION_EVIDENCE_INDEX
echo ============================================================
py -3 tools\medtas\calculation_evidence_index_v2_2.py --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
