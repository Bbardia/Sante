"""Integration tests for /users/* endpoints."""

import pytest


def _admin_token(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Admin-scoped tests
# ---------------------------------------------------------------------------


def test_create_salesman(client):
    token = _admin_token(client)
    resp = client.post(
        "/users",
        json={"username": "alice", "password": "pass1", "role": "salesman"},
        headers=_auth(token),
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["username"] == "alice"
    assert data["role"] == "salesman"


def test_list_users_includes_created(client):
    token = _admin_token(client)
    client.post(
        "/users",
        json={"username": "bob", "password": "pass2", "role": "stockman"},
        headers=_auth(token),
    )
    resp = client.get("/users", headers=_auth(token))
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "bob" in usernames
    assert "admin" in usernames


def test_search_filters_users(client):
    token = _admin_token(client)
    client.post(
        "/users",
        json={"username": "carol", "password": "p", "role": "manager"},
        headers=_auth(token),
    )
    resp = client.get("/users?search=car", headers=_auth(token))
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "carol" in usernames
    # admin should not appear (does not contain "car")
    assert "admin" not in usernames


def test_duplicate_username_returns_409(client):
    token = _admin_token(client)
    client.post(
        "/users",
        json={"username": "dave", "password": "p", "role": "salesman"},
        headers=_auth(token),
    )
    resp = client.post(
        "/users",
        json={"username": "dave", "password": "other", "role": "salesman"},
        headers=_auth(token),
    )
    assert resp.status_code == 409


def test_patch_changes_role(client):
    token = _admin_token(client)
    create_resp = client.post(
        "/users",
        json={"username": "eve", "password": "p", "role": "salesman"},
        headers=_auth(token),
    )
    user_id = create_resp.json()["id"]
    patch_resp = client.patch(
        f"/users/{user_id}",
        json={"role": "stockman"},
        headers=_auth(token),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["role"] == "stockman"


def test_delete_non_admin_user(client):
    token = _admin_token(client)
    create_resp = client.post(
        "/users",
        json={"username": "frank", "password": "p", "role": "salesman"},
        headers=_auth(token),
    )
    user_id = create_resp.json()["id"]
    del_resp = client.delete(f"/users/{user_id}", headers=_auth(token))
    assert del_resp.status_code in (200, 204)
    # Confirm it's gone
    list_resp = client.get("/users", headers=_auth(token))
    usernames = [u["username"] for u in list_resp.json()]
    assert "frank" not in usernames


def test_delete_admin_returns_403(client):
    token = _admin_token(client)
    # Find the admin user id
    list_resp = client.get("/users", headers=_auth(token))
    admin_user = next(u for u in list_resp.json() if u["username"] == "admin")
    resp = client.delete(f"/users/{admin_user['id']}", headers=_auth(token))
    assert resp.status_code == 403


def test_password_stored_hashed(client):
    token = _admin_token(client)
    plaintext = "mysecretpassword"
    create_resp = client.post(
        "/users",
        json={"username": "grace", "password": plaintext, "role": "salesman"},
        headers=_auth(token),
    )
    user_id = create_resp.json()["id"]

    # Access the DB directly via a separate session to check password_hash
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # We need to query the test DB — use the overridden get_db
    from app.main import app as fastapi_app
    from app.db import get_db

    # Call the override to get a session
    override = fastapi_app.dependency_overrides.get(get_db)
    assert override is not None, "DB override should be active"
    gen = override()
    db = next(gen)
    try:
        from app.models import User
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.password_hash != plaintext
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ---------------------------------------------------------------------------
# Non-admin (salesman) tests
# ---------------------------------------------------------------------------


def test_salesman_cannot_list_users(client):
    admin_token = _admin_token(client)
    # Create a salesman
    client.post(
        "/users",
        json={"username": "henry", "password": "pass", "role": "salesman"},
        headers=_auth(admin_token),
    )
    # Login as salesman
    login = client.post("/auth/login", json={"username": "henry", "password": "pass"})
    salesman_token = login.json()["access_token"]
    resp = client.get("/users", headers=_auth(salesman_token))
    assert resp.status_code == 403
