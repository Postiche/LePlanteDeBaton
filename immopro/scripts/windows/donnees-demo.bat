@echo off
REM Ajoute des donnees de DEMONSTRATION fictives (marquees DEMO). Suppression : purge-demo
cd /d "%~dp0..\..\backend"
.venv\Scripts\python -m app.cli seed-demo
pause
