@echo off
cd /d "%~dp0.."
echo Applies controlled master patch and creates local backup.
py -3.12 tools\K01_MASTER_COMPLETENESS_PATCH_v1.py --apply
pause
