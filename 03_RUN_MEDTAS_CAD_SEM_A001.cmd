@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call "03_RUN_MEDTAS_PIPELINE.cmd"
exit /b %ERRORLEVEL%
