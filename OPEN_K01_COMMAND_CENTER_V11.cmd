@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ==============================================================================
echo MARVILON MEDTAS - K01 Secure Priority Engineering Control Center v2.0
echo ==============================================================================
echo 1. Status model self-test
py -3 "tools\medtas\status_model_selftest_v1_8.py" --repo-root "%CD%"
if errorlevel 1 goto :fail
echo 2. Security/static self-test
py -3 "tools\medtas\center_security_selftest_v2_0.py" --repo-root "%CD%"
if errorlevel 1 goto :fail
echo 3. Controlled action-launch self-test
py -3 "tools\medtas\center_action_launch_selftest_v2_0.py" --repo-root "%CD%"
if errorlevel 1 goto :fail
echo 4. Refresh current materialized project state
py -3 "tools\medtas\project_structure_v1_7.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_release_priority_view_v1_9.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\project_view_v1_9.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_release_program_v1_9.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_p007_geometry_authority_v2_0.py" --repo-root "%CD%" >nul 2>&1
py -3 "tools\medtas\build_p007_exemplar_plan_v2_0.py" --repo-root "%CD%" >nul 2>&1
echo 5. Starting secure server build 2.0 on localhost (8790 or next free port)
echo    NOTE: if an older Center console is still open, this launcher will use the next free port.
py -3 "tools\medtas\center_server_v12.py" --repo-root "%CD%" --port 8790
set RC=%ERRORLEVEL%
if NOT %RC% EQU 0 pause
exit /b %RC%
:fail
echo.
echo COMMAND CENTER START BLOCKED: self-test failed.
pause
exit /b 30
