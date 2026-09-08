@echo off
setlocal
set "REPO=D:\BreshevEngineering\marvilon-k01"

echo ================================================================================
echo K01 CONTINUE 06
echo Starts from the already-PASS Gate04E v3 evidence. No CAD rebuild.
echo ================================================================================
echo.

if not exist "%REPO%\control\requirements\APPLY_T03_DP_TEMP_CLOSURE.ps1" (
    echo ERROR: Closure script is missing.
    echo Expected: %REPO%\control\requirements\APPLY_T03_DP_TEMP_CLOSURE.ps1
    pause
    exit /b 10
)

echo [1/6] Close T03 + pressure + accepted CFD temperature...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%REPO%\control\requirements\APPLY_T03_DP_TEMP_CLOSURE.ps1" ^
    -RepoRoot "%REPO%"
if errorlevel 1 (
    echo STOP: controlled T03/requirements closure failed.
    pause
    exit /b 20
)

echo.
echo [2/6] Run T05 compact-flange analytical screen...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%REPO%\control\calculations\RUN_T05_CLAMP_SCREEN.ps1" ^
    -RepoRoot "%REPO%"
if errorlevel 1 (
    echo HOLD: T05 screen found an engineering hold. Continue to evidence collection.
)

echo.
echo [3/6] Probe native P006 features/dimensions for production drawing compiler...
if exist "%REPO%\cad_api\drawings\p006_probe\RUN_P006_DRAWING_PROBE.cmd" (
    call "%REPO%\cad_api\drawings\p006_probe\RUN_P006_DRAWING_PROBE.cmd"
) else (
    echo HOLD: P006 drawing probe launcher is missing.
)

echo.
echo [4/6] Build FEMM screening input pack...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%REPO%\control\femm\BUILD_FEMM_SCREENING_INPUT_PACK.ps1" ^
    -RepoRoot "%REPO%"
if errorlevel 1 (
    echo HOLD: FEMM input pack is incomplete. Continue.
)

echo.
echo [5/6] Build current AI handoff ZIP...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%REPO%\control\handoff\BUILD_AI_HANDOFF.ps1" ^
    -RepoRoot "%REPO%"
if errorlevel 1 (
    echo HOLD: AI handoff build failed. Continue.
)

echo.
echo [6/6] Build module closure status...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%REPO%\control\project\BUILD_MODULE_CLOSURE_STATUS.ps1" ^
    -RepoRoot "%REPO%"

echo.
echo ================================================================================
echo CONTINUE 06 COMPLETE.
echo Core engineering next: T05 local FEA/torque, T06 service/galling, T07 P007 refresh,
echo then FEMM and production drawings.
echo ================================================================================
pause
exit /b 0
