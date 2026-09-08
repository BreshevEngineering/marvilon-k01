@echo off
cd /d "%~dp0.."
echo Gate04B v7 auto-opens/activates stable A001 even if P016 is active.
py -3.12 tools\sw_gate04b_datum_c_v7.py
pause
