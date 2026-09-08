@echo off
setlocal
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
py -3 "%ROOT%\tools\cli\k01_cli.py" --repo-root "%ROOT%" %*
exit /b %ERRORLEVEL%
