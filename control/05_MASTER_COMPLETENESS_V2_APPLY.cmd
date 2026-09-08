@echo off
cd /d "%~dp0.."
echo Applies reviewed v2 master repair and creates timestamped backup.
py -3.12 tools\K01_MASTER_COMPLETENESS_PATCH_v2.py --apply
pause
