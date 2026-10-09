# ImmoPro Entreprise

Application web privée de gestion et de recherche en immobilier d'entreprise (entrepôts, plateformes logistiques, locaux d'activité, bâtiments industriels, bureaux, terrains).

- **Backend** : Python 3.11+ · FastAPI · SQLAlchemy 2 · Alembic · Argon2id · ReportLab
- **Frontend** : React 19 · Vite · Leaflet/OpenStreetMap · PWA (manifest + service worker)
- **Base de données** : SQLite (développement, petit poste unique) ou PostgreSQL (production)
- **Déploiement** : Docker Compose + Caddy (HTTPS automatique), ou systemd + Nginx/Certbot

> Documentation : [Guide d'utilisation](docs/GUIDE-UTILISATEUR.md) · [Architecture et modèle de données](docs/ARCHITECTURE.md) · [Déploiement, sauvegarde, restauration](docs/DEPLOIEMENT.md)

## Ce qui fonctionne (vérifié par des tests)

| Domaine | État |
|---|---|
| Connexion privée, Argon2id, sessions serveur (cookies HttpOnly/Secure/SameSite=Strict), CSRF, verrouillage après 5 échecs, expiration, lien de récupération à usage unique, rôles admin/collaborateur/lecteur | ✅ |
| Tableau de bord (indicateurs, pipeline, offres par type, nouveaux biens par semaine, relances, activité) | ✅ |
| Offres : fiche complète, photos/documents protégés, archivage, doublons, provenance, export Excel/CSV, recherche avancée | ✅ |
| Demandes : critères complets, critères **impératifs** vs souhaitables, doublons | ✅ |
| Imports Excel/CSV/PDF/Word avec **validation humaine** obligatoire, aucune valeur inventée | ✅ (PDF scannés sans texte : non lus, pas d'OCR) |
| Matching bidirectionnel, score explicable sur 100, pondérations configurables, informations manquantes jamais validées, recalcul automatique | ✅ |
| Contacts : copier, appeler (`tel:`), préparer un email, proposer une visite | ✅ |
| Emails : 6 modèles, texte modifiable, copier, `mailto:`, fichier `.eml` avec fiches PDF, jamais d'envoi automatique | ✅ |
| Visites (créneaux multiples, confirmation uniquement saisie manuellement), pipeline commercial à 9 statuts, CRM, rappels, historique | ✅ |
| Fiches PDF et dossiers multi-biens | ✅ |
| Carte Leaflet, zones/rayons, liste des biens non géocodés | ✅ |
| PWA installable, aucune donnée de l'API mise en cache | ✅ |
| Sauvegardes automatiques + restauration (SQLite et PostgreSQL), journal d'audit, RGPD (export, anonymisation, opposition) | ✅ |

## Ce qui nécessite une configuration externe ou n'a pas pu être vérifié

- **BureauxLocaux / Geolocaux** : aucune API officielle n'a pu être identifiée ni testée (ces sites n'étaient pas joignables depuis l'environnement de développement). L'application **n'extrait rien automatiquement** et ne fabrique ni résultats ni URL de recherche paramétrées : elle ouvre la plateforme, affiche les critères à reporter, puis permet l'**import manuel** des annonces (URL, champs, coordonnées publiques de l'annonceur), leur contrôle de fraîcheur et leur enregistrement en base après validation. Un modèle d'URL vérifié par vous-même peut être saisi dans *Paramètres › Connecteurs*. Un connecteur API pourra être branché (`app/connectors.py`, méthode `fetch_listings`) si un accès officiel est obtenu.
- **Géocodage** : implémenté avec le service public de la Géoplateforme IGN (`data.geopf.fr/geocodage`), mais non joignable depuis l'environnement de développement : **non vérifié en conditions réelles**. En cas d'échec, l'offre reste « non géocodée » (aucune coordonnée inventée) et des coordonnées peuvent être saisies à la main.
- **Outlook classique (Windows)** : agent local facultatif `outlook-agent/` (pywin32). Les contrôles de sécurité de l'agent (écoute 127.0.0.1, origine autorisée, jeton d'appairage) ont été testés ; la création effective du brouillon via COM **n'a pas pu être testée** (pas de Windows/Outlook disponible). Le nouvel Outlook n'est pas compatible COM : utilisez le fichier `.eml` ou `mailto:`.
- **Tuiles OpenStreetMap** : usage modéré autorisé avec attribution ; pour un usage intensif, configurez un fournisseur sous contrat (*Paramètres › Général*).
- **Docker** : `Dockerfile` et `deploy/docker-compose.yml` fournis mais non exécutés ici (Docker indisponible dans l'environnement). L'application a en revanche été testée sur SQLite **et** PostgreSQL 16.
- **Navigateurs** : parcours testés automatiquement sous Chromium (bureau 1440 px et mobile 390 px tactile). Edge (Chromium) devrait se comporter de même ; **Safari/iOS n'a pas été testé** : à vérifier sur un appareil réel.

## Démarrage rapide — Windows

Prérequis : [Python 3.11+](https://www.python.org/downloads/) (cocher « Add python.exe to PATH ») et [Node.js LTS 20.19+](https://nodejs.org/).

```bat
scripts\windows\installer.bat      :: dépendances, .env avec clé aléatoire, base, compilation
scripts\windows\creer-admin.bat    :: compte administrateur (mot de passe saisi masqué)
scripts\windows\lancer.bat         :: http://127.0.0.1:8000
```

- Développement avec rechargement automatique : `scripts\windows\lancer-dev.bat` → http://localhost:5173
- Données de démonstration (fictives, marquées **DÉMO**) : `scripts\windows\donnees-demo.bat` ; suppression : `python -m app.cli purge-demo`
- Tests : `scripts\windows\tests.bat`

## Démarrage rapide — Linux / macOS

```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # puis renseigner SECRET_KEY
python -m app.cli init-db
python -m app.cli create-admin --username monidentifiant --full-name "Prénom Nom"
cd ../frontend && npm install && npm run build
cd ../backend && uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Mise en ligne HTTPS (résumé)

```bash
cp deploy/.env.production.example deploy/.env.production   # DOMAIN, SECRET_KEY, POSTGRES_PASSWORD
docker compose -f deploy/docker-compose.yml --env-file deploy/.env.production up -d --build
docker compose -f deploy/docker-compose.yml --env-file deploy/.env.production exec app python -m app.cli create-admin --username monidentifiant
```

Le DNS du domaine doit pointer vers le serveur (ports 80 et 443 ouverts) : Caddy obtient et renouvelle le certificat automatiquement. Détails, alternative sans Docker, sauvegardes et restauration : [docs/DEPLOIEMENT.md](docs/DEPLOIEMENT.md).

## Tests

```bash
cd backend && pytest -q                       # 42 tests API, sécurité, matching, imports, emails, PDF, sauvegarde
TEST_DATABASE_URL=postgresql+psycopg://… pytest -q   # même suite sur PostgreSQL
cd frontend && npm test                       # tests unitaires de l'interface
```

## Remarque sur ce dépôt

Ce dossier est hébergé dans le dépôt du site public « Le Planté de Bâton », dont le workflow GitHub Pages publie **tout le dépôt** à chaque push sur `main`. Seul le code source serait publié (aucune donnée, aucun secret : `.env` et `data/` sont exclus par `.gitignore`), mais il est recommandé de déplacer `immopro/` dans un **dépôt privé dédié** avant fusion dans `main`.
