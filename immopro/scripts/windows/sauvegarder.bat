@echo off
REM Sauvegarde immediate (base + fichiers) dans backend\data\backups
REM Pour l'automatiser : Planificateur de taches Windows > Creer une tache de base > ce fichier
cd /d "%~dp0..\..\backend"
.venv\Scripts\python -m app.cli backup
