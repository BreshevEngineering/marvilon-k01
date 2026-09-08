@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.2 - 39_BUILD_FINAL_BOM_V2_2
echo ============================================================
py -3 tools\medtas\build_bom_v2_2.py --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
