@echo off
setlocal
cd /d "%~dp0"

echo ================================================================================
echo MARVILON K01 Gate04C - ALL: BUILD -> VERIFY -> DRAWINGS
echo ================================================================================
echo Stable P003/P007/A001 are never direct write targets.
echo.

call "01_GATE04C_BUILD_ONLY.cmd"
if errorlevel 1 goto :FAIL_BUILD

call "02_GATE04C_VERIFY_ONLY.cmd"
if errorlevel 1 goto :FAIL_VERIFY

call "03_GATE04C_DRAWINGS_ONLY.cmd"
if errorlevel 1 goto :FAIL_DRAW

echo.
echo ================================================================================
echo GATE04C AUTOMATION PIPELINE PASSED
echo ================================================================================
echo CAD candidates:
echo   D:\Marvilon\K01\cad\candidates\gate04c
echo Verification:
echo   D:\Marvilon\K01\cad\candidates\gate04c\verification
echo Draft drawings:
echo   D:\Marvilon\K01\cad\drawings\gate04c_draft
echo Reports:
echo   D:\BreshevEngineering\marvilon-k01\reports\cad\current
echo.
echo IMPORTANT: this is NOT stable promotion. Run existing K01 review/interference QA.
pause
exit /b 0

:FAIL_BUILD
echo.
echo BUILD failed. Stop here. Stable CAD was not the write target.
pause
exit /b 1

:FAIL_VERIFY
echo.
echo BUILD succeeded but VERIFY failed/HOLD. Do not promote candidates.
pause
exit /b 2

:FAIL_DRAW
echo.
echo CAD BUILD + VERIFY succeeded but DRAWING generation failed/HOLD.
echo Candidate CAD remains available for QA; do not promote until drawing/API issue is reviewed.
pause
exit /b 3
