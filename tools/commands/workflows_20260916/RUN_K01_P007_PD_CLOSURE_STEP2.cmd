@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."

echo ===============================================================================
echo K01 P007 PRODUCT DEFINITION CLOSURE - STEP 2
echo SOURCE HYGIENE + PDS/NAVIGATION RECONCILIATION. NO CAD MUTATION.
echo ===============================================================================

echo [1/8] Archive confirmed superseded/history sources...
py -3 tools\repo\archive_superseded_sources_v1.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [2/8] Verify source hygiene / no stale active P007 weld authority...
py -3 tools\repo\source_hygiene_guard.py --repo-root "%CD%" --write-report
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/8] Rebuild P007/J2 Product Development System state...
py -3 tools\pds\k01_pds.py --repo-root "%CD%" status
if errorlevel 1 exit /b %ERRORLEVEL%

echo [4/8] Rebuild P007 Product Definition readiness...
py -3 tools\medtas\product_definition_guard_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [5/8] Rebuild EBOM / MBOM...
py -3 tools\medtas\build_bom_v1_9.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [6/8] Rebuild MEDTAS derived state...
py -3 tools\medtas\rebuild_medtas_state.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [7/8] Finalize exact next action to T07A...
py -3 tools\pds\p007_step2_finalize.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [8/8] Rebuild AI handoff with current PDS and archive/history excluded...
py -3 tools\medtas\ai_handoff_v2_0.py --repo-root "%CD%" --cad-root "D:\Marvilon\K01\cad"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo STATUS: PASS_P007_PD_CLOSURE_STEP2_SOURCE_HYGIENE_AND_PDS_CURRENT
echo NEXT: T07A MANUAL_CONTROLLED - existing SolidWorks Simulation, current P007 geometry
echo   STATIC:   +0.20 bar, minimum screening SF >= 2
echo   BUCKLING: -0.20 bar, first positive lambda1 >= 10
echo DO NOT AUTHOR FULL K01-D-006 YET. PRODUCT DEFINITION RELEASE GAPS REMAIN.
exit /b 0
