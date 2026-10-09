"""Sauvegarde et restauration (base + fichiers téléversés)."""
from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from .config import get_settings

log = logging.getLogger(__name__)


def _sqlite_path() -> Path:
    return Path(get_settings().database_url.removeprefix("sqlite:///"))


def create_backup(label: str = "auto") -> Path:
    s = get_settings()
    bdir = Path(s.backup_dir)
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = bdir / f"immopro-{label}-{stamp}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        if s.is_sqlite:
            dump = tmpd / "immopro.db"
            src = sqlite3.connect(_sqlite_path())
            dst = sqlite3.connect(dump)
            with dst:
                src.backup(dst)  # copie cohérente même en cours d'utilisation
            src.close()
            dst.close()
        else:
            dump = tmpd / "immopro.pgdump"
            url = s.database_url.replace("postgresql+psycopg://", "postgresql://")
            subprocess.run(["pg_dump", "--format=custom", "--no-owner", f"--file={dump}", url], check=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(dump, dump.name)
            up = Path(s.upload_dir)
            if up.exists():
                for f in up.iterdir():
                    if f.is_file():
                        zf.write(f, f"uploads/{f.name}")
            zf.writestr("manifest.json", json.dumps({"created_at": stamp, "engine": "sqlite" if s.is_sqlite else "postgresql", "label": label}))
    target.chmod(0o600)
    prune_backups()
    log.info("Sauvegarde créée : %s", target)
    return target


def prune_backups() -> None:
    s = get_settings()
    files = sorted(Path(s.backup_dir).glob("immopro-auto-*.zip"))
    for f in files[: max(0, len(files) - s.backup_keep)]:
        f.unlink(missing_ok=True)


def list_backups() -> list[dict]:
    bdir = Path(get_settings().backup_dir)
    if not bdir.exists():
        return []
    return [
        {"name": f.name, "size": f.stat().st_size, "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()}
        for f in sorted(bdir.glob("immopro-*.zip"), reverse=True)
    ]


def restore_backup(archive: Path) -> None:
    """Restaure une sauvegarde. L'application doit être ARRÊTÉE pendant la restauration."""
    s = get_settings()
    with zipfile.ZipFile(archive) as zf, tempfile.TemporaryDirectory() as tmp:
        for name in zf.namelist():
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError(f"Chemin suspect dans l'archive : {name}")
        zf.extractall(tmp)
        tmpd = Path(tmp)
        manifest = json.loads((tmpd / "manifest.json").read_text())
        if manifest["engine"] == "sqlite":
            if not s.is_sqlite:
                raise ValueError("Sauvegarde SQLite : la configuration actuelle utilise PostgreSQL.")
            dbp = _sqlite_path()
            if dbp.exists():
                shutil.copy2(dbp, dbp.with_suffix(".avant-restauration.db"))
            for suffix in ("-wal", "-shm"):
                Path(str(dbp) + suffix).unlink(missing_ok=True)
            shutil.copy2(tmpd / "immopro.db", dbp)
        else:
            url = s.database_url.replace("postgresql+psycopg://", "postgresql://")
            subprocess.run(["pg_restore", "--clean", "--if-exists", "--no-owner", f"--dbname={url}", str(tmpd / "immopro.pgdump")], check=True)
        up = Path(s.upload_dir)
        up.mkdir(parents=True, exist_ok=True)
        if (tmpd / "uploads").exists():
            for f in (tmpd / "uploads").iterdir():
                shutil.copy2(f, up / f.name)
