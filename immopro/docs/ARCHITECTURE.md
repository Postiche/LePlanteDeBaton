# Architecture et modèle de données

## Vue d'ensemble

```
Navigateur (PC, iPhone, Android, tablette) ── HTTPS ──► Caddy / Nginx ──► FastAPI (uvicorn)
   React + Vite (PWA)                                                     ├─ API /api/* (session + CSRF)
   service worker : cache des seules ressources statiques                 ├─ fichiers /api/files/* (authentifiés)
                                                                          ├─ interface compilée (frontend/dist)
Poste Windows (facultatif) : agent Outlook 127.0.0.1:8765 ◄── navigateur   └─ SQLAlchemy ─► PostgreSQL / SQLite
                                                                                          stockage fichiers (UPLOAD_DIR)
                                                                                          sauvegardes (BACKUP_DIR)
```

Une seule origine sert l'interface et l'API : les cookies de session peuvent être `SameSite=Strict`, sans CORS. L'interface compilée ne contient aucune donnée : tout passe par l'API authentifiée.

## Arborescence

```
immopro/
├── backend/
│   ├── app/
│   │   ├── config.py        configuration par variables d'environnement
│   │   ├── models.py        modèle de données (SQLAlchemy 2)
│   │   ├── security.py      Argon2id, sessions, CSRF, verrouillage, jetons de récupération
│   │   ├── matching.py      moteur de score explicable
│   │   ├── importers.py     extraction Excel/CSV/PDF/Word
│   │   ├── connectors.py    BureauxLocaux / Geolocaux (liens + import manuel)
│   │   ├── emails.py        modèles d'emails, génération .eml
│   │   ├── pdfgen.py        fiches et dossiers PDF
│   │   ├── storage.py       téléversements sécurisés
│   │   ├── backup.py        sauvegarde / restauration
│   │   ├── services.py      paramètres, doublons, recalcul des correspondances
│   │   ├── demo.py          données de démonstration (is_demo)
│   │   ├── cli.py           commandes d'administration
│   │   └── routers/         API REST
│   ├── migrations/          Alembic
│   └── tests/               pytest
├── frontend/                React (pages/, components/), public/ (manifest, sw.js, icônes)
├── outlook-agent/           agent local Windows facultatif
├── scripts/windows/         installation et lancement Windows
├── deploy/                  Docker Compose, Caddy, Nginx, systemd
└── docs/
```

## Modèle de données

| Table | Rôle | Points clés |
|---|---|---|
| `users` | comptes | hachage Argon2id, rôle `admin`/`collaborateur`/`lecteur`, `must_change_password` |
| `user_sessions` | sessions serveur | jeton stocké sous forme de HMAC-SHA256, jeton CSRF, expiration d'inactivité et absolue |
| `login_attempts` | limitation des tentatives | par identifiant et par IP |
| `password_reset_tokens` | récupération d'accès | usage unique, 30 min |
| `audit_logs` | journal des opérations | utilisateur, action, élément, IP |
| `app_settings` | paramètres | pondérations, seuil, Outlook, modèles d'URL, carte |
| `companies`, `contacts` | CRM | catégories, origine du contact, base légale, opposition à la prospection, `is_public_listing_contact` |
| `properties` | offres | tous les champs techniques et financiers ; `source_kind/name/url/ref/consulted_at` ; `geocode_status` ; `is_demo` |
| `client_requests` | demandes | listes JSON (types, communes, CP, départements, régions), centre + rayon, contraintes, `imperatives` |
| `matches` | correspondances suivies | score, score potentiel, détail JSON, statut du pipeline, écartée |
| `interactions` | historique et rappels | appel, note, email préparé/envoyé, visite, statut ; `remind_at`/`done` |
| `visits` | visites | créneaux proposés (heure locale), créneau confirmé saisi manuellement |
| `email_drafts` | emails préparés | statut : brouillon / ouvert dans la messagerie / brouillon Outlook / .eml / **envoi confirmé** |
| `documents` | photos et fichiers | rattachement polymorphe, nom de stockage aléatoire, SHA-256 |
| `import_batches` | imports en attente de validation | lignes extraites + preuves + doublons |
| `external_searches` | historique des recherches multisources | critères, liens, synthèse |
| `external_listings` | annonces externes | source, URL, date de consultation / vérification, coordonnées publiques |

Conventions : `NULL` = « non renseigné » (jamais zéro ni « non ») ; horodatages système en UTC ; créneaux de visite en heure locale ; toute donnée de démonstration porte `is_demo = true` et n'est jamais comparée à des données réelles.

## Moteur de matching

Pour chaque couple (demande, offre), six groupes pondérés sont évalués. Chaque groupe contient des contrôles (`Check`) ayant l'un des statuts : `ok`, `partiel`, `ecart`, `manquant`, `non_contraint`.

- Groupe sans contrainte → points pleins.
- Points du groupe = poids × moyenne des ratios des contrôles contraints (manquant = 0) ; le potentiel compte « manquant » comme 1.
- Élimination : contrôle déclaré impératif ET `partiel`/`ecart`. Jamais sur `manquant`.
- Localisation : correspondance commune / code postal / département / région demandés (100 %), même département (70 %) ou même région (40 %) qu'un lieu demandé, ou distance au centre (100 % dans le rayon, décroissance linéaire jusqu'à 2× le rayon).
- Surface : dans la fourchette (ou divisible dans la fourchette) ; décroissance jusqu'à −30 % / +50 %.
- Budget : prix ou loyer annuel (calculé au prorata si le bien est divisible ou si seul le loyer au m² est connu) ; décroissance jusqu'à +25 %.
- Typologie : type identique (100 %), famille proche (50 %) ; transaction compatible.
- Technique : hauteur, quais, résistance au sol, puissance, parking, accès PL.
- Disponibilité : disponible avant la date souhaitée, sinon décroissance sur 6 mois.

Les correspondances au-dessus du seuil sont stockées (pipeline, tableau de bord) et recalculées à chaque création/modification d'offre ou de demande et à chaque changement de pondérations. Les fiches calculent aussi en direct l'ensemble des couples, y compris éliminés sur demande.

## Sécurité

- Mots de passe : Argon2id (t=3, m=64 Mio, p=4), politique 12 caractères / 3 classes, hachage factice pour les identifiants inconnus (temps constant).
- Sessions : jeton aléatoire 256 bits en cookie `HttpOnly`, `Secure`, `SameSite=Strict`, préfixe `__Host-` ; expiration d'inactivité (8 h) et absolue (7 j) ; révocation à la désactivation du compte et au changement de mot de passe.
- CSRF : jeton par session exigé dans l'en-tête `X-CSRF-Token` pour toute écriture.
- En-têtes : CSP stricte (scripts `self` uniquement), HSTS, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Cache-Control: no-store` sur l'API.
- Fichiers : liste blanche d'extensions + signature binaire, refus des macros Office et archives anormales, ré-encodage des images (EXIF/GPS supprimés), stockage hors ressources publiques, téléchargement authentifié avec `Content-Security-Policy: sandbox`.
- Exports : neutralisation de l'injection de formules (CSV/Excel).
- Production : documentation de l'API désactivée, démarrage refusé sans `SECRET_KEY` robuste ou avec cookies non sécurisés.
- Agent Outlook : écoute sur 127.0.0.1 uniquement, origine autorisée + jeton d'appairage, pièces jointes limitées aux PDF, aucun appel à `Send()`.

Pistes d'amélioration : double authentification (TOTP), antivirus ClamAV sur les téléversements, OCR des PDF scannés, connecteurs API officiels si des accès sont obtenus.
