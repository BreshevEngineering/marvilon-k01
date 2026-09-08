@echo off
cd /d "%~dp0.."
py -3.12 tools\K01_DELETE_ARCHIVED_LOCKS_v1.py
pause
