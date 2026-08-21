"""Integration tests for GET /backup and POST /restore endpoints.

Design:
- monkeypatch app.db.DB_PATH to a tmp file so the real backend/database.db
  is NEVER touched.
- The client fixture already overrides get_db for its own ORM session; our
  endpoints use dbmod.DB_PATH / dbmod.engine directly, so we patch those too.
"""

import io
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

import app.db as dbmod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sqlite_db(path: Path, table_name: str = "foo") -> Path:
    """Create a minimal SQLite database at *path* with one table."""
    conn = sqlite3.connect(str(path))
    conn.execute(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    return path


def _admin_token(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def patched_client(client, tmp_path, monkeypatch):
    """client fixture extended with a patched DB_PATH pointing to a tmp file.

    Also replaces dbmod.engine with an engine pointing at the same tmp path
    so that engine.dispose() inside POST /restore doesn't touch the real DB.
    """
    fake_db = tmp_path / "database.db"
    _make_sqlite_db(fake_db, table_name="original_table")

    monkeypatch.setattr(dbmod, "DB_PATH", fake_db)

    # Provide a throwaway engine so dispose() is safe
    fake_engine = create_engine(
        f"sqlite:///{fake_db}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(dbmod, "engine", fake_engine)

    yield client, tmp_path, fake_db


# ---------------------------------------------------------------------------
# GET /backup
# ---------------------------------------------------------------------------


def test_backup_download_admin(patched_client):
    """Admin can download the DB file; response is valid SQLite bytes."""
    client, tmp_path, fake_db = patched_client
    token = _admin_token(client)

    resp = client.get("/backup", headers=_auth(token))

    assert resp.status_code == 200
    assert "application/octet-stream" in resp.headers["content-type"]
    assert resp.content[:15] == b"SQLite format 3"


def test_backup_download_manager(patched_client):
    """Manager role is allowed on GET /backup."""
    client, tmp_path, fake_db = patched_client
    # Create a manager user via admin
    token = _admin_token(client)
    client.post(
        "/users",
        json={"username": "mgr", "password": "pass", "role": "manager"},
        headers=_auth(token),
    )
    mgr_resp = client.post("/auth/login", json={"username": "mgr", "password": "pass"})
    mgr_token = mgr_resp.json()["access_token"]

    resp = client.get("/backup", headers=_auth(mgr_token))
    assert resp.status_code == 200


def test_backup_salesman_forbidden(patched_client):
    """Salesman cannot access GET /backup (403)."""
    client, tmp_path, fake_db = patched_client
    token = _admin_token(client)
    client.post(
        "/users",
        json={"username": "sale", "password": "pass", "role": "salesman"},
        headers=_auth(token),
    )
    sale_resp = client.post("/auth/login", json={"username": "sale", "password": "pass"})
    sale_token = sale_resp.json()["access_token"]

    resp = client.get("/backup", headers=_auth(sale_token))
    assert resp.status_code == 403


def test_backup_file_not_found(client, tmp_path, monkeypatch):
    """If DB_PATH does not exist, GET /backup returns 404."""
    missing = tmp_path / "nonexistent.db"
    monkeypatch.setattr(dbmod, "DB_PATH", missing)

    token = _admin_token(client)
    resp = client.get("/backup", headers=_auth(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /restore
# ---------------------------------------------------------------------------


def test_restore_valid_sqlite(patched_client):
    """Uploading a valid SQLite file replaces DB_PATH and creates a safety backup."""
    client, tmp_path, fake_db = patched_client
    token = _admin_token(client)

    # Build a DIFFERENT sqlite DB with a distinct table
    new_db_path = tmp_path / "new.db"
    _make_sqlite_db(new_db_path, table_name="new_table")
    new_bytes = new_db_path.read_bytes()

    resp = client.post(
        "/restore",
        files={"file": ("new.db", io.BytesIO(new_bytes), "application/octet-stream")},
        headers=_auth(token),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["restored"] is True
    assert data["safety_backup"] is not None  # a pre-restore backup was created

    # The DB_PATH now contains the new content (new_table should be queryable)
    conn = sqlite3.connect(str(fake_db))
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "new_table" in tables
    assert "original_table" not in tables

    # A safety backup exists in backups/
    backups_dir = fake_db.parent / "backups"
    backups = list(backups_dir.glob("sante-pre-restore-*.db"))
    assert len(backups) == 1


def test_restore_invalid_bytes_rejected(patched_client):
    """Uploading non-SQLite bytes returns 400 and leaves DB_PATH unchanged."""
    client, tmp_path, fake_db = patched_client
    token = _admin_token(client)

    original_bytes = fake_db.read_bytes()

    resp = client.post(
        "/restore",
        files={"file": ("bad.db", io.BytesIO(b"hello world"), "application/octet-stream")},
        headers=_auth(token),
    )

    assert resp.status_code == 400
    # DB_PATH must be unchanged
    assert fake_db.read_bytes() == original_bytes


def test_restore_salesman_forbidden(patched_client):
    """Salesman cannot use POST /restore (403)."""
    client, tmp_path, fake_db = patched_client
    token = _admin_token(client)
    client.post(
        "/users",
        json={"username": "sale2", "password": "pass", "role": "salesman"},
        headers=_auth(token),
    )
    sale_resp = client.post("/auth/login", json={"username": "sale2", "password": "pass"})
    sale_token = sale_resp.json()["access_token"]

    new_db_path = tmp_path / "new2.db"
    _make_sqlite_db(new_db_path)
    new_bytes = new_db_path.read_bytes()

    resp = client.post(
        "/restore",
        files={"file": ("new2.db", io.BytesIO(new_bytes), "application/octet-stream")},
        headers=_auth(sale_token),
    )
    assert resp.status_code == 403
