"""Integration tests for /products endpoints."""


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


def test_create_product(client):
    token = _login(client)
    resp = client.post(
        "/products",
        json={"name": "Espresso", "price": 2.5},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Espresso"
    assert data["price"] == 2.5
    assert "id" in data


def test_duplicate_name_returns_409(client):
    token = _login(client)
    client.post(
        "/products",
        json={"name": "Latte", "price": 3.0},
        headers=_auth(token),
    )
    resp = client.post(
        "/products",
        json={"name": "Latte", "price": 3.5},
        headers=_auth(token),
    )
    assert resp.status_code == 409


def test_list_products(client):
    token = _login(client)
    client.post("/products", json={"name": "Cappuccino", "price": 3.0}, headers=_auth(token))
    client.post("/products", json={"name": "Americano", "price": 2.0}, headers=_auth(token))
    resp = client.get("/products", headers=_auth(token))
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Cappuccino" in names
    assert "Americano" in names


def test_search_filters_products(client):
    token = _login(client)
    client.post("/products", json={"name": "Green Tea", "price": 2.0}, headers=_auth(token))
    client.post("/products", json={"name": "Black Coffee", "price": 1.5}, headers=_auth(token))
    resp = client.get("/products?search=Tea", headers=_auth(token))
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Green Tea" in names
    assert "Black Coffee" not in names


def test_patch_price(client):
    token = _login(client)
    resp = client.post(
        "/products", json={"name": "Mocha", "price": 3.5}, headers=_auth(token)
    )
    prod_id = resp.json()["id"]
    patch_resp = client.patch(
        f"/products/{prod_id}",
        json={"price": 4.0},
        headers=_auth(token),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["price"] == 4.0
    assert patch_resp.json()["name"] == "Mocha"


def test_patch_name_clash_returns_409(client):
    token = _login(client)
    r1 = client.post("/products", json={"name": "ProdA", "price": 1.0}, headers=_auth(token))
    client.post("/products", json={"name": "ProdB", "price": 2.0}, headers=_auth(token))
    prod_a_id = r1.json()["id"]
    resp = client.patch(
        f"/products/{prod_a_id}",
        json={"name": "ProdB"},
        headers=_auth(token),
    )
    assert resp.status_code == 409


def test_patch_returns_404_for_missing(client):
    token = _login(client)
    resp = client.patch("/products/9999", json={"price": 1.0}, headers=_auth(token))
    assert resp.status_code == 404


def test_delete_product_and_recipes_removed(client):
    token = _login(client)
    # Create ingredient
    ing_resp = client.post(
        "/inventory",
        json={"name": "Coffee Beans", "qty": 10.0, "unit": "kg", "price": 20.0},
        headers=_auth(token),
    )
    ing_id = ing_resp.json()["id"]

    # Create product
    prod_resp = client.post(
        "/products", json={"name": "Filter Coffee", "price": 2.0}, headers=_auth(token)
    )
    prod_id = prod_resp.json()["id"]

    # Link recipe
    recipe_resp = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.02},
        headers=_auth(token),
    )
    recipe_id = recipe_resp.json()["id"]

    # Delete product
    del_resp = client.delete(f"/products/{prod_id}", headers=_auth(token))
    assert del_resp.status_code == 200

    # Product gone
    list_resp = client.get("/products", headers=_auth(token))
    ids = [p["id"] for p in list_resp.json()]
    assert prod_id not in ids

    # Recipe gone
    recipes_resp = client.get("/recipes", headers=_auth(token))
    recipe_ids = [r["id"] for r in recipes_resp.json()]
    assert recipe_id not in recipe_ids


def test_delete_returns_404_for_missing(client):
    token = _login(client)
    resp = client.delete("/products/9999", headers=_auth(token))
    assert resp.status_code == 404


def test_stockman_cannot_access_products(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "stocky2", "stockman")
    stockman_token = _login(client, "stocky2", "pass")

    resp = client.get("/products", headers=_auth(stockman_token))
    assert resp.status_code == 403


def test_manager_can_access_products(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "mgr", "manager")
    mgr_token = _login(client, "mgr", "pass")

    resp = client.get("/products", headers=_auth(mgr_token))
    assert resp.status_code == 200
