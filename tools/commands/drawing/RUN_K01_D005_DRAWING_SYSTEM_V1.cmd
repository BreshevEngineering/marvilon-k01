@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
echo ============================================================
echo K01-D-005 / P006 - GENERIC DRAWING SYSTEM QUALIFICATION
echo NEW DRAWING. ENGINEERING REVIEW. WIP=1.
echo ============================================================
py -3 tools\medtas\drawing_system_v1.py --repo-root "%CD%" --spec control\drawings\spec\K01-D-005_P006_DRAWING_SPEC_v1.json --mode review
set RC=%ERRORLEVEL%
echo.
echo FINAL_RC=%RC%
pause
exit /b %RC%
