@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
call tools\commands\drawing\RUN_DRAWING_SYSTEM_V5_RESULT.cmd control\drawings\contracts\K01-D-005_DRAWING_CONTRACT_v2_1.json manufacturing reports\cad\drawing_system_v5\K01-D-005\current native
exit /b %ERRORLEVEL%
