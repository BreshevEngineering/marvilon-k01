@echo off
setlocal
cd /d %~dp0\..\..
py -3 tools\medtas\p007_pmi_proven_step13_current_v1.py --repo-root "%CD%" --external-package-root "D:\BreshevEngineering\Additional\k01_step13_integrated"
exit /b %ERRORLEVEL%
