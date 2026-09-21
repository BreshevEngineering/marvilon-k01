@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 tools\medtas\drawing_d7_semantic_qa_v15.py
exit /b %errorlevel%
