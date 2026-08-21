"""Integration tests for /recipes endpoints."""


def _login(client, username="admin", password="admin"):
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _setup(client, token):
    """Create one product and one ingredient, return (prod_id, ing_id)."""
    prod = client.post(
        "/products", json={"name": "Pasta", "price": 8.0}, headers=_auth(token)
    ).json()
    ing = client.post(
        "/inventory",
        json={"name": "Durum Wheat", "qty": 50.0, "unit": "kg", "price": 1.5},
        headers=_auth(token),
    ).json()
    return prod["id"], ing["id"]


def test_create_recipe_returns_names(client):
    token = _login(client)
    prod_id, ing_id = _setup(client, token)
    resp = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.2},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["product_id"] == prod_id
    assert data["ingredient_id"] == ing_id
    assert data["product_name"] == "Pasta"
    assert data["ingredient_name"] == "Durum Wheat"
    assert data["qty"] == 0.2
    assert "id" in data


def test_create_recipe_bad_product_id_returns_404(client):
    token = _login(client)
    ing = client.post(
        "/inventory",
        json={"name": "Cheese", "qty": 5.0, "unit": "kg", "price": 10.0},
        headers=_auth(token),
    ).json()
    resp = client.post(
        "/recipes",
        json={"product_id": 9999, "ingredient_id": ing["id"], "qty": 0.1},
        headers=_auth(token),
    )
    assert resp.status_code == 404


def test_create_recipe_bad_ingredient_id_returns_404(client):
    token = _login(client)
    prod = client.post(
        "/products", json={"name": "Pizza", "price": 10.0}, headers=_auth(token)
    ).json()
    resp = client.post(
        "/recipes",
        json={"product_id": prod["id"], "ingredient_id": 9999, "qty": 0.3},
        headers=_auth(token),
    )
    assert resp.status_code == 404


def test_list_recipes_filtered_by_product_id(client):
    token = _login(client)
    prod_id, ing_id = _setup(client, token)

    # Create another product + ingredient + recipe
    prod2 = client.post(
        "/products", json={"name": "Risotto", "price": 12.0}, headers=_auth(token)
    ).json()
    ing2 = client.post(
        "/inventory",
        json={"name": "Arborio Rice", "qty": 20.0, "unit": "kg", "price": 2.0},
        headers=_auth(token),
    ).json()

    # Link both
    r1 = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.2},
        headers=_auth(token),
    ).json()
    r2 = client.post(
        "/recipes",
        json={"product_id": prod2["id"], "ingredient_id": ing2["id"], "qty": 0.3},
        headers=_auth(token),
    ).json()

    # Filter by prod_id
    resp = client.get(f"/recipes?product_id={prod_id}", headers=_auth(token))
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert r1["id"] in ids
    assert r2["id"] not in ids


def test_list_recipes_no_filter_returns_all(client):
    token = _login(client)
    prod_id, ing_id = _setup(client, token)
    r1 = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.2},
        headers=_auth(token),
    ).json()
    resp = client.get("/recipes", headers=_auth(token))
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert r1["id"] in ids


def test_patch_recipe_qty(client):
    token = _login(client)
    prod_id, ing_id = _setup(client, token)
    recipe = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.2},
        headers=_auth(token),
    ).json()
    recipe_id = recipe["id"]

    patch_resp = client.patch(
        f"/recipes/{recipe_id}",
        json={"qty": 0.5},
        headers=_auth(token),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["qty"] == 0.5


def test_patch_recipe_returns_404_for_missing(client):
    token = _login(client)
    resp = client.patch("/recipes/9999", json={"qty": 1.0}, headers=_auth(token))
    assert resp.status_code == 404


def test_delete_recipe(client):
    token = _login(client)
    prod_id, ing_id = _setup(client, token)
    recipe = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.2},
        headers=_auth(token),
    ).json()
    recipe_id = recipe["id"]

    del_resp = client.delete(f"/recipes/{recipe_id}", headers=_auth(token))
    assert del_resp.status_code == 200

    # Confirm gone
    resp = client.get(f"/recipes?product_id={prod_id}", headers=_auth(token))
    ids = [r["id"] for r in resp.json()]
    assert recipe_id not in ids


def test_delete_recipe_returns_404_for_missing(client):
    token = _login(client)
    resp = client.delete("/recipes/9999", headers=_auth(token))
    assert resp.status_code == 404


def test_deleting_product_also_removes_recipe(client):
    """Covered again here to verify the cascade from products side."""
    token = _login(client)
    prod_id, ing_id = _setup(client, token)
    recipe = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.2},
        headers=_auth(token),
    ).json()
    recipe_id = recipe["id"]

    client.delete(f"/products/{prod_id}", headers=_auth(token))

    recipes_resp = client.get("/recipes", headers=_auth(token))
    ids = [r["id"] for r in recipes_resp.json()]
    assert recipe_id not in ids


def test_deleting_ingredient_also_removes_recipe(client):
    """Covered again here to verify the cascade from inventory side."""
    token = _login(client)
    prod_id, ing_id = _setup(client, token)
    recipe = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.2},
        headers=_auth(token),
    ).json()
    recipe_id = recipe["id"]

    client.delete(f"/inventory/{ing_id}", headers=_auth(token))

    recipes_resp = client.get("/recipes", headers=_auth(token))
    ids = [r["id"] for r in recipes_resp.json()]
    assert recipe_id not in ids
