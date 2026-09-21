@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
call tools\commands\drawing\RUN_DRAWING_SYSTEM_PRODUCTION.cmd control\drawings\contracts\K01-D-005_DRAWING_CONTRACT_v2_1.json reports\cad\drawing_system_v5\K01-D-005\current
exit /b %ERRORLEVEL%
