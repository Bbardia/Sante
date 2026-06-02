"""Integration tests for /auth/* endpoints."""


def test_login_admin_success(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["username"] == "admin"
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_me_with_valid_token(client):
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    token = login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_me_without_token(client):
    resp = client.get("/auth/me")
    # HTTPBearer raises 403 when no Authorization header provided
    assert resp.status_code in (401, 403)
