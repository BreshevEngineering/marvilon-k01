@echo off
cd /d "%~dp0.."
echo Open stable K01-A-001, Fully Resolved, active.
py -3.12 tools\sw_bom_projection_v2.py
pause
