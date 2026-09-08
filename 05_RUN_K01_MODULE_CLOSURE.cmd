@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
echo ================================================================================
echo K01 MODULE CLOSURE 05
echo Correct Gate04E -> close T03/T04 basis -> T05 screen -> drawing/FEMM inputs
echo ================================================================================
echo.

echo [1/7] Rebuild Gate04E with corrected v3 source...
set "GATE=%ROOT%cad_api\gates\gate04e_p006_service\RUN_GATE04E_P006_SERVICE_BUILD.cmd"
if not exist "%GATE%" (echo ERROR missing Gate04E launcher&pause&exit /b 10)
call "%GATE%"
if errorlevel 1 (echo STOP Gate04E failed&pause&exit /b 20)

echo.
echo [2/7] Close T03 + pressure + accepted CFD temperature...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%control\requirements\APPLY_T03_DP_TEMP_CLOSURE.ps1" -RepoRoot "%ROOT:~0,-1%"
if errorlevel 1 (echo STOP controlled closure failed&pause&exit /b 30)

echo.
echo [3/7] Run T05 analytical clamp/flange screen...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%control\calculations\RUN_T05_CLAMP_SCREEN.ps1" -RepoRoot "%ROOT:~0,-1%"
if errorlevel 1 (echo HOLD T05 screen failed)

echo.
echo [4/7] Probe P006 native dimensions/features for drawing compiler...
call "%ROOT%cad_api\drawings\p006_probe\RUN_P006_DRAWING_PROBE.cmd"

echo.
echo [5/7] Build FEMM screening input pack...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%control\femm\BUILD_FEMM_SCREENING_INPUT_PACK.ps1" -RepoRoot "%ROOT:~0,-1%"

echo.
echo [6/7] Build current AI handoff...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%control\handoff\BUILD_AI_HANDOFF.ps1" -RepoRoot "%ROOT:~0,-1%"

echo.
echo [7/7] Build module closure status...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%control\project\BUILD_MODULE_CLOSURE_STATUS.ps1" -RepoRoot "%ROOT:~0,-1%"

echo.
echo ================================================================================
echo CLOSURE 05 COMPLETE.
echo Next: T05 local FEA/torque process + P006 native production drawing + FEMM input freeze.
echo ================================================================================
pause
exit /b 0
