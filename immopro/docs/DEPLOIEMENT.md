# Déploiement, sauvegarde et restauration

## 1. Choix d'hébergement

Un petit serveur Linux (VPS 2 vCPU / 4 Go, Debian ou Ubuntu) suffit. L'application doit être servie **uniquement en HTTPS**, sur un nom de domaine que vous contrôlez (ex. `immo.mondomaine.fr`).

## 2. Option A — Docker Compose + Caddy (recommandée)

1. Installer Docker et le plugin Compose sur le serveur.
2. Créer un enregistrement DNS `A` (et `AAAA` si IPv6) `immo.mondomaine.fr` → IP du serveur. Ouvrir les ports 80 et 443.
3. Copier le projet sur le serveur, puis :
   ```bash
   cp deploy/.env.production.example deploy/.env.production
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # → SECRET_KEY
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # → POSTGRES_PASSWORD
   nano deploy/.env.production       # DOMAIN, SECRET_KEY, POSTGRES_PASSWORD
   chmod 600 deploy/.env.production
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env.production up -d --build
   ```
4. Créer l'administrateur (mot de passe saisi de façon masquée, jamais stocké en clair) :
   ```bash
   docker compose -f deploy/docker-compose.yml --env-file deploy/.env.production exec app \
     python -m app.cli create-admin --username monidentifiant --full-name "Prénom Nom" --email moi@mondomaine.fr
   ```
5. Ouvrir `https://immo.mondomaine.fr`. Caddy obtient et renouvelle automatiquement le certificat Let's Encrypt.

Mise à jour : `git pull` puis la même commande `up -d --build` (les migrations sont appliquées au démarrage).

## 3. Option B — sans Docker (systemd + Nginx + Certbot)

```bash
sudo adduser --system --group immopro
sudo mkdir -p /opt/immopro && sudo chown immopro: /opt/immopro   # copier le projet ici
cd /opt/immopro/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && chmod 600 .env    # APP_ENV=production, SECRET_KEY, DATABASE_URL PostgreSQL,
                                          # COOKIE_SECURE=true, TRUST_PROXY_HEADERS=true,
                                          # PUBLIC_BASE_URL=https://immo.mondomaine.fr,
                                          # UPLOAD_DIR et BACKUP_DIR en chemins absolus
cd ../frontend && npm ci && npm run build
sudo cp ../deploy/immopro.service /etc/systemd/system/ && sudo systemctl enable --now immopro
sudo cp ../deploy/nginx-immopro.conf /etc/nginx/sites-available/immopro   # adapter le domaine
sudo ln -s /etc/nginx/sites-available/immopro /etc/nginx/sites-enabled/
sudo certbot --nginx -d immo.mondomaine.fr
sudo -u immopro .venv/bin/python -m app.cli create-admin --username monidentifiant
```

PostgreSQL : `sudo -u postgres createuser -P immopro && sudo -u postgres createdb -O immopro immopro`, puis
`DATABASE_URL=postgresql+psycopg://immopro:MOT_DE_PASSE@127.0.0.1:5432/immopro`.

## 4. Mode local Windows

Voir `README.md` (scripts `scripts\windows\*.bat`). En local sur `http://`, `COOKIE_SECURE=false` est nécessaire ; il est **refusé** au démarrage en production.

Accès depuis un téléphone sur le même réseau Wi-Fi : un téléphone ne peut pas utiliser de cookies sécurisés sur une adresse `http://192.168.x.x`. Pour un usage mobile, déployez l'application en HTTPS (option A ou B).

## 5. Sécurité en production — liste de contrôle

- [ ] `APP_ENV=production` (désactive la documentation de l'API, impose `SECRET_KEY` ≥ 32 caractères et `COOKIE_SECURE=true`)
- [ ] fichiers `.env` / `.env.production` en `chmod 600`, jamais versionnés
- [ ] pare-feu : seuls 22 (SSH par clé), 80 et 443 ouverts ; PostgreSQL non exposé
- [ ] mises à jour système automatiques ; image Docker reconstruite régulièrement
- [ ] sauvegardes copiées **hors du serveur** (voir ci-dessous) et restauration testée
- [ ] comptes collaborateurs nominatifs, rôle « lecteur » pour les accès en consultation
- [ ] agent Outlook : uniquement sur les postes Windows des utilisateurs, jamais sur le serveur

## 6. Sauvegardes

- **Automatiques** : l'application crée une archive toutes les `BACKUP_INTERVAL_HOURS` heures (24 par défaut) dans `BACKUP_DIR`, et conserve les `BACKUP_KEEP` dernières. Archive = base (copie cohérente SQLite ou `pg_dump`) + fichiers téléversés + manifeste.
- **Manuelles** : *Paramètres › Sauvegardes › Sauvegarder maintenant* (téléchargeable), ou `python -m app.cli backup`, ou `scripts\windows\sauvegarder.bat`.
- **Copie externe** (indispensable) : par exemple chaque nuit
  `rsync -a /var/lib/docker/volumes/deploy_appdata/_data/backups/ sauvegarde@autre-serveur:/immopro/`
  ou un outil chiffré (restic, borg). Sous Windows : Planificateur de tâches + `sauvegarder.bat` + copie vers un disque externe ou un cloud chiffré.
- Les archives contiennent des données personnelles : stockage chiffré, accès restreint, durée de conservation définie.

## 7. Restauration

1. **Arrêter l'application** (`docker compose … stop app`, `systemctl stop immopro` ou fermer `lancer.bat`).
2. Restaurer :
   ```bash
   python -m app.cli restore /chemin/immopro-auto-AAAAMMJJ-HHMMSS.zip     # tapez OUI pour confirmer
   python -m app.cli init-db
   ```
   Avec Docker : `docker compose … run --rm app python -m app.cli restore /data/backups/<fichier>.zip`.
   Windows : `scripts\windows\restaurer.bat`.
3. Relancer l'application. Pour SQLite, l'ancienne base est conservée sous `*.avant-restauration.db`.

Une sauvegarde SQLite ne peut être restaurée que sur une configuration SQLite, et une sauvegarde PostgreSQL sur PostgreSQL (version majeure de `pg_dump` ≤ version du serveur).

## 8. Récupération d'accès

- Utilisateur ayant oublié son mot de passe : un administrateur génère un **lien de réinitialisation** (*Paramètres › Utilisateurs*), à usage unique, valable 30 minutes, à transmettre par un canal sûr.
- Administrateur unique bloqué : sur le serveur, `python -m app.cli reset-link --username monidentifiant` affiche un lien de réinitialisation. L'accès au serveur fait office de second facteur.
