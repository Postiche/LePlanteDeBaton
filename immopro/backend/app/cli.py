"""Commandes d'administration.

    python -m app.cli init-db                   # crée / met à jour le schéma (migrations Alembic)
    python -m app.cli create-admin --username jdupont [--full-name "Jean Dupont"] [--email ...]
    python -m app.cli reset-link --username jdupont   # lien de récupération à usage unique
    python -m app.cli seed-demo [--force]       # données de démonstration (refusé en production sans --force)
    python -m app.cli purge-demo                # supprime toutes les données de démonstration
    python -m app.cli backup                    # sauvegarde immédiate
    python -m app.cli restore FICHIER.zip       # restauration (application arrêtée)
    python -m app.cli recompute                 # recalcule toutes les correspondances
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import select

from .config import BASE_DIR, get_settings
from .db import SessionLocal
from .models import User


def init_db() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    command.upgrade(cfg, "head")
    print("Base de données à jour.")


def _read_password(username: str) -> str:
    from .security import password_policy_errors

    env = os.environ.pop("IMMOPRO_ADMIN_PASSWORD", None)  # usage non interactif (CI/Docker), jamais stocké
    if env:
        errs = password_policy_errors(env, username)
        if errs:
            sys.exit("Mot de passe refusé : " + " ".join(errs))
        return env
    while True:
        p1 = getpass.getpass("Mot de passe (12 caractères minimum) : ")
        errs = password_policy_errors(p1, username)
        if errs:
            print(" ".join(errs))
            continue
        if getpass.getpass("Confirmez le mot de passe : ") != p1:
            print("Les mots de passe ne correspondent pas.")
            continue
        return p1


def create_admin(username: str, full_name: str | None, email: str | None) -> None:
    from .audit import log_action
    from .security import hash_password

    username = username.strip().lower()
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.username == username))
        if existing:
            sys.exit(f"L'utilisateur « {username} » existe déjà. Utilisez reset-link pour récupérer l'accès.")
        pwd = _read_password(username)
        u = User(username=username, full_name=full_name, email=email, role="admin", password_hash=hash_password(pwd))
        db.add(u)
        db.commit()
        log_action(db, None, "administrateur_cree_cli", "user", u.id, {"username": username})
    print(f"Administrateur « {username} » créé.")


def reset_link(username: str) -> None:
    from .security import create_reset_token

    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == username.strip().lower()))
        if u is None:
            sys.exit("Utilisateur introuvable.")
        token = create_reset_token(db, u)
    s = get_settings()
    print(f"Lien valable {s.reset_token_minutes} minutes, à usage unique :")
    print(f"{s.public_base_url.rstrip('/')}/reinitialisation?token={token}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Administration ImmoPro")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    a = sub.add_parser("create-admin")
    a.add_argument("--username", required=True)
    a.add_argument("--full-name")
    a.add_argument("--email")
    r = sub.add_parser("reset-link")
    r.add_argument("--username", required=True)
    d = sub.add_parser("seed-demo")
    d.add_argument("--force", action="store_true")
    sub.add_parser("purge-demo")
    sub.add_parser("backup")
    rs = sub.add_parser("restore")
    rs.add_argument("archive")
    sub.add_parser("recompute")
    args = parser.parse_args(argv)

    if args.cmd == "init-db":
        init_db()
    elif args.cmd == "create-admin":
        create_admin(args.username, args.full_name, args.email)
    elif args.cmd == "reset-link":
        reset_link(args.username)
    elif args.cmd == "seed-demo":
        from .demo import seed_demo

        if get_settings().is_production and not args.force:
            sys.exit("Refusé en production. Ajoutez --force si vous voulez vraiment des données de démonstration (marquées DÉMO).")
        with SessionLocal() as db:
            print(seed_demo(db))
    elif args.cmd == "purge-demo":
        from .demo import purge_demo

        with SessionLocal() as db:
            print(purge_demo(db))
    elif args.cmd == "backup":
        from .backup import create_backup

        print(create_backup("manuel"))
    elif args.cmd == "restore":
        from .backup import restore_backup

        if input("La restauration remplace les données actuelles. Application arrêtée ? Tapez OUI : ") != "OUI":
            sys.exit("Annulé.")
        restore_backup(Path(args.archive))
        print("Restauration terminée. Exécutez init-db puis relancez l'application.")
    elif args.cmd == "recompute":
        from .services import recompute_all

        with SessionLocal() as db:
            print(f"{recompute_all(db)} demandes recalculées.")


if __name__ == "__main__":
    main()
