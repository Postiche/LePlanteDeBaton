import pytest

from app.config import get_settings

from .test_flows import PROP


@pytest.mark.skipif(not get_settings().is_sqlite, reason="sauvegarde PostgreSQL testée via pg_dump")
def test_backup_and_restore_sqlite(auth_client):
    from app import backup
    from app.db import reset_engine

    auth_client.post("/api/properties", json=PROP)
    r = auth_client.post("/api/backups")
    assert r.status_code == 200
    name = r.json()["name"]
    assert any(b["name"] == name for b in auth_client.get("/api/backups").json()["backups"])
    pid = auth_client.get("/api/properties").json()["items"][0]["id"]
    auth_client.delete(f"/api/properties/{pid}")
    assert auth_client.get("/api/properties").json()["total"] == 0
    reset_engine()
    backup.restore_backup(get_settings().backup_dir / name)
    reset_engine()
    assert auth_client.get("/api/properties").json()["total"] == 1
