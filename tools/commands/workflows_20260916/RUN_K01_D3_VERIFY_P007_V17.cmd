@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo [1/4] Run contract-driven D3 on SAME V12 exemplar...
py -3 -B tools\medtas\drawing_d3_verify_v17.py
set "D3_RC=%ERRORLEVEL%"

echo [2/4] Rebuild MEDTAS derived state after D3 evidence update...
py -3 -B tools\medtas\rebuild_medtas_state.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/4] Rebuild AI handoff so current D3 evidence is transport-closed...
py -3 -B tools\medtas\ai_handoff_v2_0.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [4/4] Re-run assurance coherence after D3...
py -3 -B tools\assurance\center_assurance_coherence.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

exit /b %D3_RC%
