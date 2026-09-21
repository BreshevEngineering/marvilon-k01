@echo off
setlocal
cd /d "%~dp0\..\..\.."
if "%~2"=="" (
  echo USAGE: RUN_K01_DRAWING_IMPORT_MANUAL_FINISH_V1.cmd ^<DRAWING_ID^> ^<ISO_FINISH.SLDDRW^> [PDF]
  exit /b 2
)
py -3 tools\medtas\drawing_candidate_lifecycle_v1.py --repo-root "%CD%" import-manual --drawing-id "%~1" --drawing "%~2" --pdf "%~3"
exit /b %ERRORLEVEL%
