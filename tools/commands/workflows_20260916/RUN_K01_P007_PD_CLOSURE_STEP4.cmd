@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."

echo ===============================================================================
echo K01 P007 PRODUCT DEFINITION CLOSURE - STEP 4
echo C07/C08/C11 RADIAL ENVELOPE RELEASE. NO CAD MUTATION.
echo ===============================================================================

echo [1/7] Apply EDR-029 semantic source updates...
py -3 tools\pds\p007_step4_close_radial_envelope.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [2/7] Verify source hygiene...
py -3 tools\repo\source_hygiene_guard.py --repo-root "%CD%" --write-report
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/7] Rebuild P007/J2 PDS...
py -3 tools\pds\k01_pds.py --repo-root "%CD%" status
if errorlevel 1 exit /b %ERRORLEVEL%

echo [4/7] Rebuild Product Definition...
py -3 tools\medtas\product_definition_guard_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [5/7] Rebuild EBOM / MBOM and MEDTAS...
py -3 tools\medtas\build_bom_v1_9.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%
py -3 tools\medtas\rebuild_medtas_state.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [6/7] Rebuild AI handoff...
py -3 tools\medtas\ai_handoff_v2_0.py --repo-root "%CD%" --cad-root "D:\Marvilon\K01\cad"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [7/7] Final status...
echo STATUS: PASS_P007_PD_CLOSURE_STEP4_C07_C08_C11
echo NEXT: C01/C05/C06/blind-end tolerance/form closure via T05/process evidence. No drawing authoring yet.
exit /b 0
