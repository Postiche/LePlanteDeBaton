@echo off
REM Lance l'application (API + interface compilee) sur http://127.0.0.1:8000
cd /d "%~dp0..\..\backend"
.venv\Scripts\python -m app.cli init-db
start "" http://127.0.0.1:8000
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
