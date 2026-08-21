"""Tests for GET /debts and POST /debts/{sale_id}/pay."""


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
        json={"product_id": bread["id"], "ingredient_id": flour["id"], "qty": 1.0},
        headers=_auth(token),
    )
    return flour["id"], bread["id"]


def _make_paid_sale(client, token, product_id):
    resp = client.post(
        "/sales",
        json={"items": [{"product_id": product_id, "qty": 1}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_unpaid_sale(client, token, product_id, customer_id):
    resp = client.post(
        "/sales",
        json={
            "items": [{"product_id": product_id, "qty": 1}],
            "customer_id": customer_id,
            "pay_later": True,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /debts
# ---------------------------------------------------------------------------


def test_unpaid_sale_appears_in_debts(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    cust = client.post(
        "/customers", json={"name": "Debtor"}, headers=_auth(token)
    ).json()

    unpaid = _make_unpaid_sale(client, token, bread_id, cust["id"])

    resp = client.get("/debts", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = [s["id"] for s in data]
    assert unpaid["sale_id"] in ids


def test_paid_sale_not_in_debts(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    cust = client.post(
        "/customers", json={"name": "Payer"}, headers=_auth(token)
    ).json()

    paid = _make_paid_sale(client, token, bread_id)
    unpaid = _make_unpaid_sale(client, token, bread_id, cust["id"])

    resp = client.get("/debts", headers=_auth(token))
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert paid["sale_id"] not in ids
    assert unpaid["sale_id"] in ids


def test_debts_ordered_newest_first(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    cust = client.post(
        "/customers", json={"name": "Debtor2"}, headers=_auth(token)
    ).json()

    d1 = _make_unpaid_sale(client, token, bread_id, cust["id"])
    d2 = _make_unpaid_sale(client, token, bread_id, cust["id"])

    resp = client.get("/debts", headers=_auth(token))
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert ids.index(d2["sale_id"]) < ids.index(d1["sale_id"])


# ---------------------------------------------------------------------------
# POST /debts/{sale_id}/pay
# ---------------------------------------------------------------------------


def test_pay_debt_flips_status(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    cust = client.post(
        "/customers", json={"name": "Payer3"}, headers=_auth(token)
    ).json()

    unpaid = _make_unpaid_sale(client, token, bread_id, cust["id"])
    sale_id = unpaid["sale_id"]

    # Appears in debts before paying
    debts_before = client.get("/debts", headers=_auth(token)).json()
    assert sale_id in [s["id"] for s in debts_before]

    # Pay it
    pay_resp = client.post(f"/debts/{sale_id}/pay", headers=_auth(token))
    assert pay_resp.status_code == 200, pay_resp.text
    data = pay_resp.json()
    assert data["id"] == sale_id
    assert data["payment_status"] == "Paid"

    # No longer in debts
    debts_after = client.get("/debts", headers=_auth(token)).json()
    assert sale_id not in [s["id"] for s in debts_after]


def test_pay_debt_idempotent(client):
    """Paying an already-paid sale just returns it (no error)."""
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    cust = client.post(
        "/customers", json={"name": "Idempotent"}, headers=_auth(token)
    ).json()

    unpaid = _make_unpaid_sale(client, token, bread_id, cust["id"])
    sale_id = unpaid["sale_id"]

    # Pay once
    r1 = client.post(f"/debts/{sale_id}/pay", headers=_auth(token))
    assert r1.status_code == 200
    assert r1.json()["payment_status"] == "Paid"

    # Pay again — should still be 200 and Paid
    r2 = client.post(f"/debts/{sale_id}/pay", headers=_auth(token))
    assert r2.status_code == 200
    assert r2.json()["payment_status"] == "Paid"


def test_pay_nonexistent_sale_404(client):
    token = _login(client)
    resp = client.post("/debts/9999/pay", headers=_auth(token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Role access
# ---------------------------------------------------------------------------


def test_salesman_can_access_debts(client):
    token = _login(client)
    _, bread_id = _setup_bread(client, token)
    _create_user(client, token, "sally", "salesman")
    cust = client.post(
        "/customers", json={"name": "RoleDebtor"}, headers=_auth(token)
    ).json()
    unpaid = _make_unpaid_sale(client, token, bread_id, cust["id"])
    sale_id = unpaid["sale_id"]

    sales_token = _login(client, "sally", "pass")

    r = client.get("/debts", headers=_auth(sales_token))
    assert r.status_code == 200

    r2 = client.post(f"/debts/{sale_id}/pay", headers=_auth(sales_token))
    assert r2.status_code == 200


def test_stockman_forbidden_on_debts(client):
    token = _login(client)
    _create_user(client, token, "stocky", "stockman")
    stock_token = _login(client, "stocky", "pass")

    r = client.get("/debts", headers=_auth(stock_token))
    assert r.status_code == 403

    r2 = client.post("/debts/1/pay", headers=_auth(stock_token))
    assert r2.status_code == 403
