"""Integration tests for /sales checkout endpoint (the financial core)."""


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


def _setup_bread(client, token):
    """flour ingredient (100kg @ 2), bread product (price 5), recipe bread<-flour qty 2.

    Returns (flour_id, bread_id).
    """
    flour = client.post(
        "/inventory",
        json={"name": "flour", "qty": 100.0, "unit": "kg", "price": 2.0},
        headers=_auth(token),
    ).json()
    bread = client.post(
        "/products", json={"name": "bread", "price": 5.0}, headers=_auth(token)
    ).json()
    client.post(
        "/recipes",
        json={"product_id": bread["id"], "ingredient_id": flour["id"], "qty": 2.0},
        headers=_auth(token),
    )
    return flour["id"], bread["id"]


def _flour(client, token, flour_id):
    items = client.get("/inventory", headers=_auth(token)).json()
    return next(i for i in items if i["id"] == flour_id)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_checkout_basic_deducts_inventory(client):
    token = _login(client)
    flour_id, bread_id = _setup_bread(client, token)

    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 3}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subtotal"] == 15.0
    assert data["discount_pct"] == 0
    assert data["discount_amount"] == 0
    assert data["total"] == 15.0
    assert data["payment_status"] == "Paid"
    assert data["customer_name"] is None
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["product_name"] == "bread"
    assert item["qty"] == 3
    assert item["unit_price"] == 5.0
    assert item["line_total"] == 15.0

    # flour: 100 - 3*2 = 94 ; total_value: 200 - 6*2 = 188 ; avg stays 2.0
    f = _flour(client, token, flour_id)
    assert f["qty"] == 94.0
    assert f["total_value"] == 188.0
    assert f["avg_price"] == 2.0

    # Sale + SaleItem persisted, retrievable via GET
    sale_id = data["sale_id"]
    got = client.get(f"/sales/{sale_id}", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["items"][0]["qty"] == 3


def test_checkout_with_discount(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 3}], "discount_pct": 10},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subtotal"] == 15.0
    assert data["discount_pct"] == 10
    assert data["discount_amount"] == 1.5
    assert data["total"] == 13.5


def test_checkout_insufficient_stock_no_mutation(client):
    token = _login(client)
    flour_id, bread_id = _setup_bread(client, token)
    before = _flour(client, token, flour_id)

    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1000}]},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["message"] == "Insufficient stock"
    assert len(detail["shortages"]) >= 1

    # Inventory unchanged
    after = _flour(client, token, flour_id)
    assert after["qty"] == before["qty"]
    assert after["total_value"] == before["total_value"]


def test_pay_later_without_customer_400(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1}], "pay_later": True},
        headers=_auth(token),
    )
    assert resp.status_code == 400


def test_pay_later_with_customer_creates_unpaid(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    cust = client.post(
        "/customers", json={"name": "Debtor"}, headers=_auth(token)
    ).json()

    resp = client.post(
        "/sales",
        json={
            "items": [{"product_id": bread_id, "qty": 1}],
            "pay_later": True,
            "customer_id": cust["id"],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["payment_status"] == "Unpaid"
    assert data["customer_name"] == "Debtor"

    got = client.get(f"/sales/{data['sale_id']}", headers=_auth(token)).json()
    assert got["payment_status"] == "Unpaid"
    assert got["customer_name"] == "Debtor"


def test_checkout_unknown_customer_404(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1}], "customer_id": 9999},
        headers=_auth(token),
    )
    assert resp.status_code == 404


def test_product_without_recipe_changes_no_inventory(client):
    token = _login(client)
    flour_id, _ = _setup_bread(client, token)
    # A product with no recipe
    water = client.post(
        "/products", json={"name": "water", "price": 1.0}, headers=_auth(token)
    ).json()
    before = _flour(client, token, flour_id)

    resp = client.post(
        "/sales",
        json={"items": [{"product_id": water["id"], "qty": 5}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 5.0

    after = _flour(client, token, flour_id)
    assert after["qty"] == before["qty"]
    assert after["total_value"] == before["total_value"]


def test_empty_cart_400(client):
    token = _login(client)
    resp = client.post("/sales", json={"items": []}, headers=_auth(token))
    assert resp.status_code == 400


def test_qty_zero_or_negative_400(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 0}]},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": -3}]},
        headers=_auth(token),
    )
    assert resp.status_code == 400


def test_unknown_product_404(client):
    token = _login(client)
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": 9999, "qty": 1}]},
        headers=_auth(token),
    )
    assert resp.status_code == 404


def test_get_sale_404(client):
    token = _login(client)
    resp = client.get("/sales/9999", headers=_auth(token))
    assert resp.status_code == 404


def test_negative_discount_pct_400(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1}], "discount_pct": -5},
        headers=_auth(token),
    )
    assert resp.status_code == 400


def test_over_100_discount_pct_400(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1}], "discount_pct": 150},
        headers=_auth(token),
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Role access
# ---------------------------------------------------------------------------


def test_salesman_can_checkout(client):
    admin_token = _login(client)
    _, bread_id = _setup_bread(client, admin_token)
    _create_user(client, admin_token, "sally", "salesman")
    sales_token = _login(client, "sally", "pass")
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1}]},
        headers=_auth(sales_token),
    )
    assert resp.status_code == 200, resp.text


def test_stockman_cannot_checkout(client):
    admin_token = _login(client)
    _, bread_id = _setup_bread(client, admin_token)
    _create_user(client, admin_token, "stocky", "stockman")
    stock_token = _login(client, "stocky", "pass")
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": bread_id, "qty": 1}]},
        headers=_auth(stock_token),
    )
    assert resp.status_code == 403
