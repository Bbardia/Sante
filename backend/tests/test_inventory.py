"""Integration tests for /inventory endpoints."""


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
# Core inventory operations
# ---------------------------------------------------------------------------


def test_add_new_ingredient(client):
    token = _login(client)
    resp = client.post(
        "/inventory",
        json={"name": "Flour", "qty": 10.0, "unit": "kg", "price": 2.0, "reorder_level": 5.0},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Flour"
    assert data["qty"] == 10.0
    assert data["total_value"] == 20.0
    assert data["avg_price"] == 2.0
    assert data["reorder_level"] == 5.0
    assert data["unit"] == "kg"


def test_add_stock_merges_same_name(client):
    token = _login(client)
    # First addition: 10 kg @ 2.0/kg → total_value=20
    client.post(
        "/inventory",
        json={"name": "Sugar", "qty": 10.0, "unit": "kg", "price": 2.0},
        headers=_auth(token),
    )
    # Second addition: 5 kg @ 3.0/kg → total_value += 15 → 35; qty=15
    resp = client.post(
        "/inventory",
        json={"name": "Sugar", "qty": 5.0, "unit": "kg", "price": 3.0},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["qty"] == 15.0
    assert data["total_value"] == 35.0
    # avg_price = round(35/15, 2) = 2.33
    assert data["avg_price"] == round(35 / 15, 2)


def test_add_stock_merge_is_case_insensitive(client):
    token = _login(client)
    client.post(
        "/inventory",
        json={"name": "Salt", "qty": 10.0, "unit": "kg", "price": 1.0},
        headers=_auth(token),
    )
    # "SALT" should merge with "Salt"
    resp = client.post(
        "/inventory",
        json={"name": "SALT", "qty": 5.0, "unit": "kg", "price": 2.0},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["qty"] == 15.0


def test_list_inventory(client):
    token = _login(client)
    client.post(
        "/inventory",
        json={"name": "Apple", "qty": 5.0, "unit": "pcs", "price": 1.0},
        headers=_auth(token),
    )
    client.post(
        "/inventory",
        json={"name": "Banana", "qty": 3.0, "unit": "pcs", "price": 0.5},
        headers=_auth(token),
    )
    resp = client.get("/inventory", headers=_auth(token))
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json()]
    assert "Apple" in names
    assert "Banana" in names


def test_search_filters_inventory(client):
    token = _login(client)
    client.post(
        "/inventory",
        json={"name": "Olive Oil", "qty": 2.0, "unit": "L", "price": 5.0},
        headers=_auth(token),
    )
    client.post(
        "/inventory",
        json={"name": "Vinegar", "qty": 1.0, "unit": "L", "price": 3.0},
        headers=_auth(token),
    )
    resp = client.get("/inventory?search=Olive", headers=_auth(token))
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json()]
    assert "Olive Oil" in names
    assert "Vinegar" not in names


def test_patch_name_unit_reorder(client):
    token = _login(client)
    resp = client.post(
        "/inventory",
        json={"name": "Eggs", "qty": 12.0, "unit": "pcs", "price": 0.2},
        headers=_auth(token),
    )
    item_id = resp.json()["id"]

    patch_resp = client.patch(
        f"/inventory/{item_id}",
        json={"name": "Free Range Eggs", "unit": "dozen", "reorder_level": 2.0},
        headers=_auth(token),
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["name"] == "Free Range Eggs"
    assert data["unit"] == "dozen"
    assert data["reorder_level"] == 2.0
    # qty and total_value should be unchanged
    assert data["qty"] == 12.0


def test_patch_returns_404_for_missing(client):
    token = _login(client)
    resp = client.patch(
        "/inventory/9999",
        json={"unit": "g"},
        headers=_auth(token),
    )
    assert resp.status_code == 404


def test_patch_name_clash_returns_409(client):
    token = _login(client)
    r1 = client.post(
        "/inventory",
        json={"name": "ItemA", "qty": 1.0, "unit": "kg", "price": 1.0},
        headers=_auth(token),
    )
    client.post(
        "/inventory",
        json={"name": "ItemB", "qty": 1.0, "unit": "kg", "price": 1.0},
        headers=_auth(token),
    )
    item_a_id = r1.json()["id"]
    resp = client.patch(
        f"/inventory/{item_a_id}",
        json={"name": "ItemB"},
        headers=_auth(token),
    )
    assert resp.status_code == 409


def test_delete_removes_ingredient_and_its_recipes(client):
    token = _login(client)
    # Create ingredient
    ing_resp = client.post(
        "/inventory",
        json={"name": "Tomato", "qty": 5.0, "unit": "kg", "price": 1.0},
        headers=_auth(token),
    )
    ing_id = ing_resp.json()["id"]

    # Create a product and link a recipe
    prod_resp = client.post(
        "/products",
        json={"name": "Tomato Soup", "price": 5.0},
        headers=_auth(token),
    )
    prod_id = prod_resp.json()["id"]
    recipe_resp = client.post(
        "/recipes",
        json={"product_id": prod_id, "ingredient_id": ing_id, "qty": 0.5},
        headers=_auth(token),
    )
    recipe_id = recipe_resp.json()["id"]

    # Delete the ingredient
    del_resp = client.delete(f"/inventory/{ing_id}", headers=_auth(token))
    assert del_resp.status_code == 200

    # Ingredient gone
    list_resp = client.get("/inventory", headers=_auth(token))
    ids = [i["id"] for i in list_resp.json()]
    assert ing_id not in ids

    # Recipe should also be gone
    recipes_resp = client.get(f"/recipes?product_id={prod_id}", headers=_auth(token))
    recipe_ids = [r["id"] for r in recipes_resp.json()]
    assert recipe_id not in recipe_ids


def test_delete_returns_404_for_missing(client):
    token = _login(client)
    resp = client.delete("/inventory/9999", headers=_auth(token))
    assert resp.status_code == 404


def test_reset_zeroes_all(client):
    token = _login(client)
    client.post(
        "/inventory",
        json={"name": "Pepper", "qty": 10.0, "unit": "g", "price": 0.1},
        headers=_auth(token),
    )
    client.post(
        "/inventory",
        json={"name": "Cumin", "qty": 5.0, "unit": "g", "price": 0.2},
        headers=_auth(token),
    )
    resp = client.post("/inventory/reset", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["reset"] == 2

    items = client.get("/inventory", headers=_auth(token)).json()
    for item in items:
        assert item["qty"] == 0.0
        assert item["total_value"] == 0.0
        assert item["avg_price"] == 0.0


# ---------------------------------------------------------------------------
# Role access tests
# ---------------------------------------------------------------------------


def test_stockman_can_access_inventory(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "stocky", "stockman")
    stockman_token = _login(client, "stocky", "pass")

    resp = client.get("/inventory", headers=_auth(stockman_token))
    assert resp.status_code == 200


def test_salesman_cannot_access_inventory(client):
    admin_token = _login(client)
    _create_user(client, admin_token, "sally", "salesman")
    salesman_token = _login(client, "sally", "pass")

    resp = client.get("/inventory", headers=_auth(salesman_token))
    assert resp.status_code == 403
