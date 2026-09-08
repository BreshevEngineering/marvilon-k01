@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.2 - 36_BUILD_TECHNICAL_FILTER_MAP
echo ============================================================
py -3 tools\medtas\technical_filter_map_v2_2.py --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
