@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
call "cad_api\solidworks_2018_proven\drawing_annotate_existing_v1\RUN_K01_DRAWING_ANNOTATE_EXISTING_V1.cmd" "cad_api\solidworks_2018_proven\drawing_annotate_existing_v1\jobs\K01-D-005_ANNOTATE_CURRENT_V1.json"
exit /b %ERRORLEVEL%
