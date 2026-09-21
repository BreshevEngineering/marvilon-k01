@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."

echo ===============================================================================
echo K01 P007 PRODUCT DEFINITION CLOSURE - STEP 1
echo EDR-025 route/BOM reconciliation. NO CAD MUTATION.
echo ===============================================================================

echo [1/3] Rebuild P007 Product Definition...
py -3 tools\medtas\product_definition_guard_v11.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [2/3] Rebuild EBOM / MBOM from canonical CAD semantic state + controlled registries...
py -3 tools\medtas\build_bom_v1_9.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/3] Rebuild MEDTAS derived state...
py -3 tools\medtas\rebuild_medtas_state.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo EXPECTED ENGINEERING EFFECT:
echo   - C10 legacy permanent-weld ambiguity removed from active P007 definition
echo   - active P007 route = monolithic machined 316L with integral blind end
echo   - NM-P007-WELD-PROCESS removed from active MBOM
echo   - MBOM-P007-WELDED-CONSTRUCTION superseded by monolithic representation
echo   - Product Definition remains HOLD for other real release blockers
echo.
echo CURRENT REPORTS:
echo   reports\control\K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json
echo   reports\medtas\bom\current\K01_EBOM_VERIFY_A001_v1_9.json
echo   reports\medtas\bom\current\K01_MBOM_VERIFY_A001_v1_9.json
exit /b 0
