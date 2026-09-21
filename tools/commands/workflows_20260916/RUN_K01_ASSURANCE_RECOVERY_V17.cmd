@echo off
setlocal
cd /d "%~dp0\..\..\.."

echo [1/5] Requalify SAME V12 exemplar to current D1 without CAD mutation...
py -3 -B tools\assurance\d006_exemplar_requalify_v17.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [2/5] Quarantine legacy dependency state and repair transition contract...
py -3 -B tools\assurance\assurance_recovery_v17.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/5] Rebuild authoritative MEDTAS derived state...
py -3 -B tools\medtas\rebuild_medtas_state.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [4/5] Rebuild AI handoff including referenced runtime evidence...
py -3 -B tools\medtas\ai_handoff_v2_0.py --repo-root "%CD%"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [5/5] Re-run assurance coherence...
py -3 -B tools\assurance\center_assurance_coherence.py --repo-root "%CD%"
exit /b %ERRORLEVEL%
