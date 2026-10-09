@echo off
REM Agent Outlook local facultatif (Windows + Outlook classique)
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
REM Indiquez ici l'adresse de votre instance ImmoPro (plusieurs adresses séparées par des virgules)
if "%IMMOPRO_ORIGIN%"=="" set IMMOPRO_ORIGIN=http://localhost:5173,http://127.0.0.1:8000
.venv\Scripts\python immopro_outlook_agent.py
pause
