@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 CAD CANONICAL HASH INVARIANCE QUALIFICATION v1.6
echo ============================================================
py -3 "tools\medtas\cad_hash_invariance_test_v1_6.py" --repo-root "%CD%"
set RC=%ERRORLEVEL%
py -3 "tools\medtas\rebuild_medtas_state.py" --repo-root "%CD%"
echo.
if "%RC%"=="0" (
  echo HASH QUALIFICATION PASS.
) else if "%RC%"=="1" (
  echo HASH QUALIFICATION HOLD - semantic drift was proven by successful exports.
) else (
  echo HASH QUALIFICATION BLOCKED - exporter did not complete; no conclusion about canonicalization.
)
pause
exit /b %RC%
