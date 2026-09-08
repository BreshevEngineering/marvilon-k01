@echo off
cd /d "%~dp0.."
echo This is MASTER PATCH V2. Output must show B007 qty_design='AR', NOT 2.
py -3.12 tools\K01_MASTER_COMPLETENESS_PATCH_v2.py
pause
