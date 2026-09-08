@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 MEDTAS v2.0 - priority engineering release pipeline
echo Root: %CD%
echo ============================================================
py -3 "tools\medtas\pipeline_v2_0.py" --repo-root "%CD%"
set RC=%ERRORLEVEL%
echo.
if %RC% EQU 0 (
  echo PIPELINE COMPLETE - inspect the priority frontier in Command Center.
) else (
  echo PIPELINE RETURNED HOLD/ERROR - inspect the generated reports; current evidence is preserved.
)
echo Start control center with: OPEN_K01_COMMAND_CENTER_V11.cmd
pause
exit /b %RC%
