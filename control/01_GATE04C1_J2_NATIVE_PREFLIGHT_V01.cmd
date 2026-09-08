@echo off
setlocal
cd /d "%~dp0.."
echo ================================================================================
echo K01 Gate04C1 - J2 NATIVE PREFLIGHT / READ-ONLY
echo ================================================================================
echo Stable A001 will be opened/activated automatically.
echo NO CAD DOCUMENT WILL BE SAVED OR MODIFIED.
echo.
py tools\sw_gate04c1_j2_native_preflight_v01.py
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
echo Report: reports\cad\current\K01_GATE04C1_J2_NATIVE_PREFLIGHT.json
echo.
pause
exit /b %RC%
