@echo off
setlocal
cd /d "%~dp0.."
echo ================================================================================
echo K01 Gate04C1 v03 - DIRECT-PART NATIVE AUDIT / READ-ONLY
echo ================================================================================
echo This version bypasses A001 assembly COM traversal completely.
echo It opens P003 and P007 directly by stable file path.
echo NO CAD DOCUMENT WILL BE SAVED OR MODIFIED.
echo.
py tools\sw_gate04c1_direct_part_native_audit_v03.py
set RC=%ERRORLEVEL%
echo.
echo Exit code: %RC%
echo Report: reports\cad\current\K01_GATE04C1_DIRECT_PART_NATIVE_AUDIT.json
echo.
pause
exit /b %RC%
