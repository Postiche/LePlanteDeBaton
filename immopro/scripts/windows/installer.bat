@echo off
REM ==========================================================================
REM  ImmoPro Entreprise - installation locale Windows
REM  Prérequis : Python 3.11+ (python.org, cocher "Add to PATH") et Node.js 20.19+ LTS
REM ==========================================================================
setlocal
cd /d "%~dp0..\.."
echo [1/5] Environnement Python...
if not exist backend\.venv ( py -3 -m venv backend\.venv 2>nul || python -m venv backend\.venv )
backend\.venv\Scripts\python -m pip install --upgrade pip >nul
backend\.venv\Scripts\pip install -r backend\requirements-dev.txt || goto :erreur
echo [2/5] Fichier de configuration...
if not exist backend\.env (
  copy backend\.env.example backend\.env >nul
  for /f %%k in ('backend\.venv\Scripts\python -c "import secrets;print(secrets.token_urlsafe(48))"') do (
    powershell -NoProfile -Command "(Get-Content backend\.env) -replace '^SECRET_KEY=$','SECRET_KEY=%%k' | Set-Content backend\.env -Encoding UTF8"
  )
  echo     backend\.env cree avec une cle secrete aleatoire.
)
echo [3/5] Base de donnees...
pushd backend
.venv\Scripts\python -m app.cli init-db || goto :erreur
popd
echo [4/5] Dependances de l'interface...
pushd frontend
call npm install --no-audit --no-fund || goto :erreur
echo [5/5] Compilation de l'interface...
call npm run build || goto :erreur
popd
echo.
echo Installation terminee.
echo  - Creez le compte administrateur : scripts\windows\creer-admin.bat
echo  - Lancez l'application        : scripts\windows\lancer.bat  (http://127.0.0.1:8000)
echo  - Mode developpement           : scripts\windows\lancer-dev.bat (http://localhost:5173)
pause
exit /b 0
:erreur
echo ERREUR pendant l'installation.
pause
exit /b 1
