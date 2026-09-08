@echo off
cd /d "%~dp0.."
echo This modifies/saves stable CAD CUSTOM PROPERTIES only.
py -3.12 tools\sw_sync_master_properties_v1.py --apply
pause
