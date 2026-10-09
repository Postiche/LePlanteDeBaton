@echo off
REM Restaure une sauvegarde. ARRETEZ d'abord l'application.
cd /d "%~dp0..\..\backend"
set /p ARCHIVE=Chemin complet du fichier .zip de sauvegarde : 
.venv\Scripts\python -m app.cli restore "%ARCHIVE%"
.venv\Scripts\python -m app.cli init-db
pause
