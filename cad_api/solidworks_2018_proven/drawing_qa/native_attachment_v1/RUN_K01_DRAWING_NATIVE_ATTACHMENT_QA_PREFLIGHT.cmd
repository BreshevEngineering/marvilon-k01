@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
powershell -NoProfile -ExecutionPolicy Bypass -File "cad_api\solidworks_2018_proven\drawing_qa\native_attachment_v1\K01_DRAWING_NATIVE_ATTACHMENT_QA.ps1" --runtime-probe
exit /b %ERRORLEVEL%
