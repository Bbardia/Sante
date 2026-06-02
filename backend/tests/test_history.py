"""Tests for GET /sales (Sales History list with search + date range)."""
from datetime import date


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
    """Set up flour ingredient, bread product, milk product (no recipe), and recipes.

    Returns (flour_id, bread_id, milk_id).
    """
    flour = client.post(
        "/inventory",
        json={"name": "flour", "qty": 200.0, "unit": "kg", "price": 2.0},
        headers=_auth(token),
    ).json()
    bread = client.post(
        "/products", json={"name": "bread", "price": 5.0}, headers=_auth(token)
    ).json()
    milk = client.post(
        "/products", json={"name": "milk", "price": 3.0}, headers=_auth(token)
    ).json()
    client.post(
        "/recipes",
        json={"product_id": bread["id"], "ingredient_id": flour["id"], "qty": 1.0},
        headers=_auth(token),
    )
    return flour["id"], bread["id"], milk["id"]


def _make_sale(client, token, product_id, qty=1, customer_id=None, pay_later=False):
    payload = {"items": [{"product_id": product_id, "qty": qty}]}
    if customer_id is not None:
        payload["customer_id"] = customer_id
    if pay_later:
        payload["pay_later"] = True
    resp = client.post("/sales", json=payload, headers=_auth(token))
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Basic list + order
# ---------------------------------------------------------------------------


def test_history_returns_newest_first(client):
    token = _login(client)
    _, bread_id, milk_id = _setup_products(client, token)

    s1 = _make_sale(client, token, bread_id, qty=1)
    s2 = _make_sale(client, token, bread_id, qty=2)
    s3 = _make_sale(client, token, milk_id, qty=1)

    resp = client.get("/sales", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 3
    # Newest first
    ids = [s["id"] for s in data]
    assert ids == [s3["sale_id"], s2["sale_id"], s1["sale_id"]]


def test_history_item_count_and_customer_name(client):
    token = _login(client)
    _, bread_id, milk_id = _setup_products(client, token)

    cust = client.post(
        "/customers", json={"name": "Alice"}, headers=_auth(token)
    ).json()

    # Sale with customer and 2 items
    sale_resp = client.post(
        "/sales",
        json={
            "items": [
                {"product_id": bread_id, "qty": 1},
                {"product_id": milk_id, "qty": 2},
            ],
            "customer_id": cust["id"],
        },
        headers=_auth(token),
    )
    assert sale_resp.status_code == 200
    sale_id = sale_resp.json()["sale_id"]

    # Sale without customer and 1 item
    anon_resp = _make_sale(client, token, milk_id)
    anon_id = anon_resp["sale_id"]

    resp = client.get("/sales", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    by_id = {s["id"]: s for s in data}

    assert by_id[sale_id]["customer_name"] == "Alice"
    assert by_id[sale_id]["item_count"] == 2

    assert by_id[anon_id]["customer_name"] is None
    assert by_id[anon_id]["item_count"] == 1


# ---------------------------------------------------------------------------
# Search by product name
# ---------------------------------------------------------------------------


def test_search_by_product_name(client):
    token = _login(client)
    _, bread_id, milk_id = _setup_products(client, token)

    bread_sale = _make_sale(client, token, bread_id)
    milk_sale = _make_sale(client, token, milk_id)

    resp = client.get("/sales?search=brea", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    ids = [s["id"] for s in data]
    assert bread_sale["sale_id"] in ids
    assert milk_sale["sale_id"] not in ids


def test_search_case_insensitive_product(client):
    token = _login(client)
    _, bread_id, _ = _setup_products(client, token)

    sale = _make_sale(client, token, bread_id)

    resp = client.get("/sales?search=BREAD", headers=_auth(token))
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert sale["sale_id"] in ids


# ---------------------------------------------------------------------------
# Search by customer name
# ---------------------------------------------------------------------------


def test_search_by_customer_name(client):
    token = _login(client)
    _, bread_id, _ = _setup_products(client, token)

    alice = client.post(
        "/customers", json={"name": "Alice"}, headers=_auth(token)
    ).json()
    bob = client.post(
        "/customers", json={"name": "Bob"}, headers=_auth(token)
    ).json()

    alice_sale = _make_sale(client, token, bread_id, customer_id=alice["id"])
    bob_sale = _make_sale(client, token, bread_id, customer_id=bob["id"])

    resp = client.get("/sales?search=alice", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    ids = [s["id"] for s in data]
    assert alice_sale["sale_id"] in ids
    assert bob_sale["sale_id"] not in ids


# ---------------------------------------------------------------------------
# Date range filter
# ---------------------------------------------------------------------------


def test_date_range_includes_today(client):
    token = _login(client)
    _, bread_id, _ = _setup_products(client, token)

    sale = _make_sale(client, token, bread_id)
    today = date.today().isoformat()

    resp = client.get(f"/sales?start={today}&end={today}", headers=_auth(token))
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert sale["sale_id"] in ids


def test_date_range_future_start_returns_empty(client):
    token = _login(client)
    _, bread_id, _ = _setup_products(client, token)

    _make_sale(client, token, bread_id)

    resp = client.get("/sales?start=2099-01-01&end=2099-12-31", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_bad_date_format_returns_400(client):
    token = _login(client)
    resp = client.get("/sales?start=01-01-2025", headers=_auth(token))
    assert resp.status_code == 400

    resp = client.get("/sales?end=not-a-date", headers=_auth(token))
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# payment_status field present
# ---------------------------------------------------------------------------


def test_history_includes_payment_status(client):
    token = _login(client)
    _, bread_id, _ = _setup_products(client, token)

    cust = client.post(
        "/customers", json={"name": "Debtor"}, headers=_auth(token)
    ).json()
    paid_sale = _make_sale(client, token, bread_id)
    unpaid_sale = _make_sale(
        client, token, bread_id, customer_id=cust["id"], pay_later=True
    )

    resp = client.get("/sales", headers=_auth(token))
    assert resp.status_code == 200
    by_id = {s["id"]: s for s in resp.json()}
    assert by_id[paid_sale["sale_id"]]["payment_status"] == "Paid"
    assert by_id[unpaid_sale["sale_id"]]["payment_status"] == "Unpaid"
