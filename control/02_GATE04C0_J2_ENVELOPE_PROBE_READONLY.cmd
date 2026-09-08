@echo off
cd /d "%~dp0.."
echo READ-ONLY: evaluates J2 flange/M3 packaging and nearby assembly envelope.
py -3.12 tools\sw_gate04c0_probe_j2_envelope.py
pause
