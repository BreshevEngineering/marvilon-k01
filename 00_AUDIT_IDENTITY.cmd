@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo K01 stable native identity audit v2.0
echo Reads actual native paths from the raw SOLIDWORKS API snapshot.
echo No files are renamed by this command.
echo ============================================================
py -3 "tools\medtas\audit_identity_v2_0.py" --repo-root "%CD%"
pause
