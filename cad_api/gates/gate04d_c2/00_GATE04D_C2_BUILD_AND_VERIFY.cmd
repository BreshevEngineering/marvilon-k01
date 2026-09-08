@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo MARVILON K01 Gate04D-C2 - BUILD + VERIFY
echo ================================================================================
echo C2 study baseline: OD33 round / 3xM2.5 / PCD26.5.
echo Stable P003/P007/A001 are never direct write targets.
echo.
call "01_GATE04D_C2_BUILD_ONLY.cmd"
if errorlevel 1 (
  echo.
  echo BUILD HOLD. Verification was not run.
  pause
  exit /b 1
)
echo.
call "02_GATE04D_C2_VERIFY_ONLY.cmd"
if errorlevel 1 (
  echo.
  echo VERIFY HOLD. Candidate build is preserved for diagnosis.
  pause
  exit /b 2
)
echo.
echo Gate04D-C2 BUILD + VERIFY PASSED.
echo Do not promote. Mechanical/thermal/service/technology gates are still OPEN.
pause
