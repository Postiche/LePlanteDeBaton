@echo off
REM Cree le compte administrateur initial (le mot de passe est saisi de facon masquee, jamais stocke en clair)
cd /d "%~dp0..\..\backend"
set /p USERNAME_ADMIN=Identifiant administrateur : 
set /p FULLNAME_ADMIN=Nom complet : 
.venv\Scripts\python -m app.cli create-admin --username "%USERNAME_ADMIN%" --full-name "%FULLNAME_ADMIN%"
pause
