"""Integration tests for /customers endpoints."""


def _login(client, username="admin", password="admin"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_user(client, token, username, role):
    resp = client.post(
        "/users",
        json={"username": username, "password": "pass", "role": role},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_customer(client):
    token = _login(client)
    resp = client.post(
        "/customers",
        json={"name": "Alice", "discount": 10.0},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alice"
    assert data["discount"] == 10.0
    assert "id" in data


def test_create_customer_default_discount_zero(client):
    token = _login(client)
    resp = client.post(
        "/customers",
        json={"name": "Bob"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    assert resp.json()["discount"] == 0.0


def test_create_duplicate_name_returns_409(client):
    token = _login(client)
    client.post("/customers", json={"name": "Carol"}, headers=_auth(token))
    resp = client.post("/customers", json={"name": "Carol"}, headers=_auth(token))
    assert resp.status_code == 409


def test_create_negative_discount_returns_400(client):
    token = _login(client)
    resp = client.post(
        "/customers",
        json={"name": "Dave", "discount": -5.0},
        headers=_auth(token),
    )
    assert resp.status_code == 400


def test_list_customers_ordered_by_name(client):
    token = _login(client)
    client.post("/customers", json={"name": "Zoe"}, headers=_auth(token))
    client.post("/customers", json={"name": "Anna"}, headers=_auth(token))
    resp = client.get("/customers", headers=_auth(token))
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert names == sorted(names)
    assert "Zoe" in names
    assert "Anna" in names


def test_list_customers_search_filter(client):
    token = _login(client)
    client.post("/customers", json={"name": "Charlie Brown"}, headers=_auth(token))
    client.post("/customers", json={"name": "Lucy"}, headers=_auth(token))
    resp = client.get("/customers?search=Charlie", headers=_auth(token))
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Charlie Brown" in names
    assert "Lucy" not in names


def test_patch_customer(client):
    token = _login(client)
    cust = client.post(
        "/customers", json={"name": "Eve", "discount": 5.0}, headers=_auth(token)
    ).json()
    resp = client.patch(
        f"/customers/{cust['id']}",
        json={"name": "Eve Updated", "discount": 15.0},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Eve Updated"
    assert data["discount"] == 15.0


def test_patch_customer_404(client):
    token = _login(client)
    resp = client.patch("/customers/9999", json={"name": "X"}, headers=_auth(token))
    assert resp.status_code == 404


def test_patch_customer_name_clash_409(client):
    token = _login(client)
    client.post("/customers", json={"name": "Frank"}, headers=_auth(token))
    c2 = client.post("/customers", json={"name": "Grace"}, headers=_auth(token)).json()
    resp = client.patch(
        f"/customers/{c2['id']}", json={"name": "Frank"}, headers=_auth(token)
    )
    assert resp.status_code == 409


def test_delete_customer(client):
    token = _login(client)
    cust = client.post("/customers", json={"name": "Heidi"}, headers=_auth(token)).json()
    resp = client.delete(f"/customers/{cust['id']}", headers=_auth(token))
    assert resp.status_code == 200
    listed = client.get("/customers", headers=_auth(token)).json()
    assert cust["id"] not in [c["id"] for c in listed]


def test_delete_customer_404(client):
    token = _login(client)
    resp = client.delete("/customers/9999", headers=_auth(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Role access
# ---------------------------------------------------------------------------


def test_salesman_can_access_customers(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "sally", "salesman")
    sales_token = _login(client, "sally", "pass")
    resp = client.get("/customers", headers=_auth(sales_token))
    assert resp.status_code == 200


def test_stockman_cannot_access_customers(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "stocky", "stockman")
    stock_token = _login(client, "stocky", "pass")
    resp = client.get("/customers", headers=_auth(stock_token))
    assert resp.status_code == 403
