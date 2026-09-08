@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ================================================================================
echo K01 MODULE CLOSURE 04
echo Engineering first. No MEDTAS redesign.
echo ================================================================================
echo.

set "CLOSE_PS=%ROOT%control\requirements\APPLY_T03_DP_TEMP_CLOSURE.ps1"
if not exist "%CLOSE_PS%" (
  echo ERROR: missing "%CLOSE_PS%"
  pause
  exit /b 10
)

echo [1/5] Close T03 + pressure + accepted CFD temperature basis...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CLOSE_PS%" -RepoRoot "%ROOT:~0,-1%"
if errorlevel 1 (
  echo STOP: controlled closure failed.
  pause
  exit /b 20
)

echo.
echo [2/5] Probe native P006 model for the first professional drawing...
set "PROBE=%ROOT%cad_api\drawings\p006_probe\RUN_P006_DRAWING_PROBE.cmd"
if exist "%PROBE%" (
  call "%PROBE%"
) else (
  echo HOLD: drawing probe launcher missing: "%PROBE%"
)

echo.
echo [3/5] Build FEMM screening input pack...
set "FEMM=%ROOT%control\femm\BUILD_FEMM_SCREENING_INPUT_PACK.ps1"
if exist "%FEMM%" (
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%FEMM%" -RepoRoot "%ROOT:~0,-1%"
) else (
  echo HOLD: FEMM input-pack script missing.
)

echo.
echo [4/5] Build module closure status...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%control\project\BUILD_MODULE_CLOSURE_STATUS.ps1" -RepoRoot "%ROOT:~0,-1%"

echo.
echo [5/5] Build repository consolidation PLAN only...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%control\repo\BUILD_REPO_CONSOLIDATION_PLAN.ps1" -RepoRoot "%ROOT:~0,-1%"

echo.
echo ================================================================================
echo CLOSURE 04 COMPLETE.
echo Next engineering calculation: T05 clamp/preload/M2.5/local flange contact.
echo ================================================================================
pause
exit /b 0
