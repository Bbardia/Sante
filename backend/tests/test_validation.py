"""Validation tests for common user-entered numeric and text fields."""


def _login(client, username="admin", password="admin"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_product_name_must_not_be_blank(client):
    token = _login(client)
    resp = client.post(
        "/products",
        json={"name": "   ", "price": 2.5},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_product_price_must_not_be_negative(client):
    token = _login(client)
    resp = client.post(
        "/products",
        json={"name": "Espresso", "price": -1},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_inventory_qty_and_price_must_be_positive(client):
    token = _login(client)
    resp = client.post(
        "/inventory",
        json={"name": "Beans", "qty": 0, "unit": "kg", "price": -5},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_customer_discount_must_be_between_0_and_100(client):
    token = _login(client)
    resp = client.post(
        "/customers",
        json={"name": "VIP", "discount": 150},
        headers=_auth(token),
    )
    assert resp.status_code == 422
