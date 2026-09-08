@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set /p STEPFILE=Full path to STEP file: 
py -3 "tools\medtas\step_canonical_hash_v1_4.py" "%STEPFILE%"
pause
