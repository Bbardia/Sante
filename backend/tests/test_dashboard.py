"""Integration tests for GET /dashboard endpoint."""

from datetime import datetime, timedelta


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


def _setup_products(client, token):
    """Create flour ingredient, bread product (price 10), cake product (price 20),
    plus recipes for both so checkout succeeds.

    Returns (flour_id, bread_id, cake_id).
    """
    flour = client.post(
        "/inventory",
        json={"name": "flour_dash", "qty": 1000.0, "unit": "kg", "price": 1.0},
        headers=_auth(token),
    ).json()
    bread = client.post(
        "/products", json={"name": "bread_dash", "price": 10.0}, headers=_auth(token)
    ).json()
    cake = client.post(
        "/products", json={"name": "cake_dash", "price": 20.0}, headers=_auth(token)
    ).json()
    # minimal recipes so checkout deducts inventory without shortfall
    client.post(
        "/recipes",
        json={"product_id": bread["id"], "ingredient_id": flour["id"], "qty": 0.1},
        headers=_auth(token),
    )
    client.post(
        "/recipes",
        json={"product_id": cake["id"], "ingredient_id": flour["id"], "qty": 0.1},
        headers=_auth(token),
    )
    return flour["id"], bread["id"], cake["id"]


# ---------------------------------------------------------------------------
# today revenue & sales_count
# ---------------------------------------------------------------------------


def test_today_revenue_and_count(client):
    token = _login(client)
    _, bread_id, cake_id = _setup_products(client, token)

    # Make 2 sales: bread qty=2 → total 20, cake qty=1 → total 20
    # Actually bread price=10 qty=2 → 20, cake price=20 qty=1 → 20 → sum 40
    # Let's do simple: bread qty=2 (20) and bread qty=1 (10) → 30, count=2
    r1 = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 2}]},
        headers=_auth(token),
    )
    assert r1.status_code == 200, r1.text

    r2 = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1}]},
        headers=_auth(token),
    )
    assert r2.status_code == 200, r2.text

    resp = client.get("/dashboard", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["today"]["revenue"] == 30.0
    assert data["today"]["sales_count"] == 2


# ---------------------------------------------------------------------------
# top_products ordering
# ---------------------------------------------------------------------------


def test_top_products_ordering(client):
    """bread_dash sold qty=5, cake_dash sold qty=3 → bread first."""
    token = _login(client)
    _, bread_id, cake_id = _setup_products(client, token)

    client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 5}]},
        headers=_auth(token),
    )
    client.post(
        "/sales",
        json={"items": [{"product_id": cake_id, "qty": 3}]},
        headers=_auth(token),
    )

    resp = client.get("/dashboard", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    top = resp.json()["top_products"]

    assert len(top) >= 2
    # bread_dash has higher total qty (5 > 3) → must be first
    names = [p["product"] for p in top]
    assert names.index("bread_dash") < names.index("cake_dash")
    # check qty values
    by_name = {p["product"]: p["qty"] for p in top}
    assert by_name["bread_dash"] == 5
    assert by_name["cake_dash"] == 3


def test_top_products_max_5(client):
    """At most 5 products returned even if more exist."""
    token = _login(client)
    # Create 6 distinct products, each with a recipe
    flour = client.post(
        "/inventory",
        json={"name": "flour_top5", "qty": 10000.0, "unit": "kg", "price": 1.0},
        headers=_auth(token),
    ).json()

    for i in range(6):
        p = client.post(
            "/products",
            json={"name": f"prod_top5_{i}", "price": 1.0},
            headers=_auth(token),
        ).json()
        client.post(
            "/recipes",
            json={"product_id": p["id"], "ingredient_id": flour["id"], "qty": 0.1},
            headers=_auth(token),
        )
        client.post(
            "/sales",
            json={"items": [{"product_id": p["id"], "qty": float(i + 1)}]},
            headers=_auth(token),
        )

    resp = client.get("/dashboard", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()["top_products"]) <= 5


# ---------------------------------------------------------------------------
# low_stock
# ---------------------------------------------------------------------------


def test_low_stock_appears_when_qty_le_reorder_level(client):
    token = _login(client)
    # Create an inventory item with qty=3, then set reorder_level=5 (qty < reorder_level)
    item = client.post(
        "/inventory",
        json={"name": "low_item", "qty": 3.0, "unit": "pcs", "price": 1.0},
        headers=_auth(token),
    ).json()
    # Set reorder_level via PATCH
    patch = client.patch(
        f"/inventory/{item['id']}",
        json={"reorder_level": 5.0},
        headers=_auth(token),
    )
    assert patch.status_code == 200

    resp = client.get("/dashboard", headers=_auth(token))
    assert resp.status_code == 200
    low = resp.json()["low_stock"]
    names = [i["name"] for i in low]
    assert "low_item" in names

    # Check the returned object structure
    entry = next(i for i in low if i["name"] == "low_item")
    assert entry["qty"] == 3.0
    assert entry["reorder_level"] == 5.0
    assert "unit" in entry


def test_low_stock_eq_reorder_level_appears(client):
    """qty == reorder_level also qualifies as low stock."""
    token = _login(client)
    item = client.post(
        "/inventory",
        json={"name": "eq_item", "qty": 5.0, "unit": "pcs", "price": 1.0},
        headers=_auth(token),
    ).json()
    client.patch(
        f"/inventory/{item['id']}",
        json={"reorder_level": 5.0},
        headers=_auth(token),
    )

    resp = client.get("/dashboard", headers=_auth(token))
    low_names = [i["name"] for i in resp.json()["low_stock"]]
    assert "eq_item" in low_names


def test_low_stock_zero_reorder_never_appears(client):
    """reorder_level == 0 (default) must never appear in low_stock."""
    token = _login(client)
    client.post(
        "/inventory",
        json={"name": "no_reorder", "qty": 0.0, "unit": "pcs", "price": 1.0},
        headers=_auth(token),
    )
    resp = client.get("/dashboard", headers=_auth(token))
    low_names = [i["name"] for i in resp.json()["low_stock"]]
    assert "no_reorder" not in low_names


def test_low_stock_sufficient_qty_does_not_appear(client):
    """qty > reorder_level must not appear."""
    token = _login(client)
    item = client.post(
        "/inventory",
        json={"name": "ok_item", "qty": 100.0, "unit": "pcs", "price": 1.0},
        headers=_auth(token),
    ).json()
    client.patch(
        f"/inventory/{item['id']}",
        json={"reorder_level": 10.0},
        headers=_auth(token),
    )
    resp = client.get("/dashboard", headers=_auth(token))
    low_names = [i["name"] for i in resp.json()["low_stock"]]
    assert "ok_item" not in low_names


# ---------------------------------------------------------------------------
# Role access
# ---------------------------------------------------------------------------


def test_salesman_can_access_dashboard(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "sally_dash", "salesman")
    sales_token = _login(client, "sally_dash", "pass")
    resp = client.get("/dashboard", headers=_auth(sales_token))
    assert resp.status_code == 200, resp.text


def test_stockman_cannot_access_dashboard(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "stocky_dash", "stockman")
    stock_token = _login(client, "stocky_dash", "pass")
    resp = client.get("/dashboard", headers=_auth(stock_token))
    assert resp.status_code == 403
