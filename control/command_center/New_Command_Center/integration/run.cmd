@echo off
setlocal
set "K01_ROOT=%~dp0"
if defined K01_PYTHON goto custom_python
py -3 "%K01_ROOT%tools\run.py" %*
exit /b %ERRORLEVEL%
:custom_python
"%K01_PYTHON%" "%K01_ROOT%tools\run.py" %*
exit /b %ERRORLEVEL%
