@echo off
setlocal
cd /d "%~dp0"
echo ================================================================================
echo K01 ENGINEERING RECOVERY 02 - DIRECT PATH
echo Infrastructure only where it blocks engineering.
echo ================================================================================
echo.

echo [1/5] Stable core preflight...
call "%~dp000_MEDTAS_PREFLIGHT.cmd"
if errorlevel 1 (
  echo STOP: core preflight failed.
  pause
  exit /b 10
)

echo.
echo [2/5] Gate04E P006 candidate + full assembly verify...
call "%~dp0cad_api\gates\gate04e_p006_service\RUN_GATE04E_P006_SERVICE_BUILD.cmd"
if errorlevel 1 (
  echo STOP: Gate04E failed. Return its complete compiler/runtime output.
  pause
  exit /b 20
)

echo.
echo [3/5] FEMM solver fingerprint...
call "%~dp0control\femm\CHECK_FEMM_INSTALL.cmd"
if errorlevel 1 (
  echo HOLD: FEMM fingerprint failed, but Gate04E has completed.
)

echo.
echo [4/5] Normalize current BOM for review...
call "%~dp0control\bom\NORMALIZE_BOM.cmd"
if errorlevel 1 (
  echo HOLD: BOM normalization failed.
)

echo.
echo [5/5] Git classification...
call "%~dp0control\git\RUN_K01_GIT_CLASSIFY.cmd"
if errorlevel 1 (
  echo HOLD: Git classification failed.
)

echo.
echo ================================================================================
echo RECOVERY RUN COMPLETE.
echo Next engineering work: pressure requirement -> T04/T05 -> T06/T07 -> FEMM.
echo ================================================================================
pause
exit /b 0
