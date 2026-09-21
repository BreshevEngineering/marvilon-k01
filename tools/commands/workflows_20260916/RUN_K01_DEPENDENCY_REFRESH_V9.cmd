@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo [1/3] Rebuild safe derived Product Definition contract...
py -3 tools\medtas\product_definition_guard_v8.py
set PD_RC=%ERRORLEVEL%

echo [2/3] Recompute authoritative MEDTAS freshness state...
py -3 tools\medtas\rebuild_medtas_state.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/3] Build focused D006 dependency/rebuild plan...
py -3 tools\medtas\change_impact_v9.py --repo-root "%CD%" scan-current --target K01.DRAWING.D006.PROJECTION
if errorlevel 1 exit /b %ERRORLEVEL%

if not "%PD_RC%"=="0" (
  echo STATUS: HOLD_PRODUCT_DEFINITION_DERIVED_REFRESH
  exit /b %PD_RC%
)
echo STATUS: PASS_DEPENDENCY_REFRESH_V9
exit /b 0
