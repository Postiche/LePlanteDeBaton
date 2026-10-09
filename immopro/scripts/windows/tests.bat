@echo off
cd /d "%~dp0..\..\backend"
.venv\Scripts\python -m pytest -q
cd ..\frontend
call npm test
pause
