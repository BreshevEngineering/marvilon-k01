@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo USAGE: RUN_K01_D006_REGISTER_EXEMPLAR_V1.cmd ^<K01-D-006_ISO_FINISH.SLDDRW^> [PDF]
  exit /b 2
)
py -3 tools\medtas\drawing_candidate_lifecycle_v1.py --repo-root "%CD%" register-exemplar --drawing-id K01-D-006 --part-id K01-P-007 --drawing "%~1" --pdf "%~2" --output-root "D:\Marvilon\K01\cad\drawings\candidates\K01-D-006"
exit /b %ERRORLEVEL%
