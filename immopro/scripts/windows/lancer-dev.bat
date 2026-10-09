@echo off
REM Mode developpement : API avec rechargement automatique + interface Vite (http://localhost:5173)
cd /d "%~dp0..\.."
start "ImmoPro API" cmd /k "cd backend && .venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
start "ImmoPro Interface" cmd /k "cd frontend && npm run dev"
timeout /t 4 >nul
start "" http://localhost:5173
