@echo off
setlocal EnableExtensions
cd /d "%~dp0"
py -3 "tools\medtas\audit_identity_v2_0.py" --repo-root "%CD%"
py -3 "tools\medtas\build_identity_migration_plan_v2_0.py" --repo-root "%CD%"
pause
