@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 Gate04D-C2R1 - BUILD + VERIFY + INTERFERENCE
echo ================================================================================
echo C2R1 fixes the proven C2 pilot/P006-head collision.
echo Stable P003/P007/A001 are never direct write targets.
echo.
call "01_GATE04D_C2R1_BUILD_ONLY.cmd"
if errorlevel 1 (echo BUILD HOLD.&pause&exit /b 1)
call "02_GATE04D_C2R1_VERIFY_ONLY.cmd"
if errorlevel 1 (echo VERIFY HOLD.&pause&exit /b 2)
call "03_GATE04D_C2R1_INTERFERENCE_QA.cmd"
if errorlevel 1 (echo INTERFERENCE HOLD.&pause&exit /b 3)
echo.
echo Gate04D-C2R1 CAD + ASSEMBLY + INTERFERENCE PASSED.
echo Production promotion remains blocked by seal/preload, local strength,
echo thermal/service, P007 structural refresh, BOM/drawings and FEMM gates.
pause
exit /b 0
