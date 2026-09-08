@echo off
setlocal
cd /d "%~dp0"

echo ================================================================================
echo K01 NEXT ENGINEERING STEP - DIRECT PATH
echo MEDTAS UI is not required for this workflow.
echo ================================================================================
echo.

echo [1/3] MEDTAS core preflight...
call "%~dp000_MEDTAS_PREFLIGHT.cmd"
if errorlevel 1 (
  echo.
  echo STOP: infrastructure preflight failed.
  pause
  exit /b 10
)

echo.
echo [2/3] Gate04E P006 service candidate + full candidate assembly...
call "%~dp0cad_api\gates\gate04e_p006_service\RUN_GATE04E_P006_SERVICE_BUILD.cmd"
if errorlevel 1 (
  echo.
  echo STOP: Gate04E failed. Return the compiler/runtime output only.
  pause
  exit /b 20
)

echo.
echo [3/3] FEMM solver fingerprint...
call "%~dp0control\femm\CHECK_FEMM_INSTALL.cmd"
if errorlevel 1 (
  echo.
  echo Gate04E passed; FEMM fingerprint remains open.
  pause
  exit /b 30
)

echo.
echo ================================================================================
echo ENGINEERING CHECKPOINT PASSED:
echo - MEDTAS core contract
echo - P006 Gate04E candidate/full-assembly stage
echo - FEMM solver fingerprint
echo.
echo Next engineering gates: pressure requirement -> T04/T05 -> T06/T07 -> FEMM screening.
echo ================================================================================
pause
exit /b 0
