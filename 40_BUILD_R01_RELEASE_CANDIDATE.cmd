@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.2 - 40_BUILD_R01_RELEASE_CANDIDATE
echo ============================================================
py -3 tools\medtas\build_r01_release_candidate_v2_2.py --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
