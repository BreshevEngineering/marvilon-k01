@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.2 - 31C_VERIFY_FINAL_ASSEMBLY_PROMOTION
echo ============================================================
py -3 tools\medtas\final_assembly_promotion_v2_2.py --repo-root "%CD%" --mode verify
set RC=%ERRORLEVEL%
echo.
echo Return code: %RC%
pause
exit /b %RC%
