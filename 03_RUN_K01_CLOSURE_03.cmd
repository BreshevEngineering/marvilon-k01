@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 CLOSURE 03
echo Correct Gate04E evidence -> close T03/DP -> probe P006 drawing -> build FEMM inputs
echo ================================================================================
echo.

echo [1/5] Rebuild Gate04E with corrected SOLIDWORKS PlaneParams contract...
call "%~dp0cad_api\gates\gate04e_p006_service\RUN_GATE04E_P006_SERVICE_BUILD.cmd"
if errorlevel 1 (
  echo STOP: corrected Gate04E failed.
  pause
  exit /b 20
)

echo.
echo [2/5] Apply controlled T03 + differential-pressure closure...
call "%~dp0control\requirements\APPLY_T03_DP_CLOSURE.cmd"
if errorlevel 1 (
  echo STOP: T03/DP closure failed.
  pause
  exit /b 30
)

echo.
echo [3/5] Probe native P006 features/dimensions for the drawing compiler...
call "%~dp0cad_api\drawings\p006_probe\RUN_P006_DRAWING_PROBE.cmd"
if errorlevel 1 (
  echo HOLD: P006 drawing probe failed. Mechanical closure remains valid.
)

echo.
echo [4/5] Build FEMM screening input pack...
call "%~dp0control\femm\BUILD_FEMM_SCREENING_INPUT_PACK.cmd"

echo.
echo [5/5] Build current AI handoff ZIP...
call "%~dp0control\handoff\BUILD_AI_HANDOFF.cmd"

echo.
echo ================================================================================
echo CLOSURE 03 COMPLETE.
echo T03 should now be closed.
echo Next technical focus is T04 local temperature/media -> T05 clamp/preload.
echo ================================================================================
pause
exit /b 0
