@echo off
setlocal
cd /d "D:\BreshevEngineering\marvilon-k01"
call "cad_api\solidworks_2018_proven\rotational_family_v1\RUN_K01_ROTATIONAL_DRAWING_API.cmd" "cad_api\solidworks_2018_proven\rotational_family_v1\specs\K01-D-005_P006_ROUGH_BUILD_R1.json"
exit /b %ERRORLEVEL%
