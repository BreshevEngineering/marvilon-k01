@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.2 - 31_COMPILE_FINAL_ASSEMBLY_PROMOTION
echo ============================================================
py -3 tools\medtas\compile_packandgo_v2_2.py --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
