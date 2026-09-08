@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ================================================================================
echo K01 BOM PROPERTY PROJECTION - APPLY CONTROLLED TEXT METADATA
echo Geometry and native material assignment are NOT changed.
echo Backups: D:\Marvilon\K01\cad\property_backups\YYYYMMDD
echo ================================================================================
set /p ACK=Type APPLY_METADATA to continue: 
if /I not "%ACK%"=="APPLY_METADATA" (echo CANCELLED&pause&exit /b 2)

call "03_BOM_PROPERTY_PROJECTION_DRY_RUN.cmd"
if errorlevel 1 (echo Dry-run did not pass. APPLY blocked.&pause&exit /b 3)

"bin\K01_BOM_PropertyProjection.exe" --apply
set APPLYRC=%ERRORLEVEL%
if NOT %APPLYRC% EQU 0 (echo APPLY failed/held. BOM refresh blocked.&pause&exit /b %APPLYRC%)

echo.
echo Metadata APPLY passed. Rebuilding C2R1 BOM and reconciliation...
call "RUN_K01_BOM_PIPELINE_C2R1.cmd"
set BOMRC=%ERRORLEVEL%
echo.
if %BOMRC% EQU 0 echo BOM PIPELINE PASSED.
if NOT %BOMRC% EQU 0 echo BOM remains HOLD because engineering release blockers and/or metadata issues remain.
pause
exit /b %BOMRC%
