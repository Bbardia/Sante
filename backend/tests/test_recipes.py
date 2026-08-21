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


# ---------------------------------------------------------------------------
# PUT /recipes/product/{product_id} — set a product's full recipe in one call
# ---------------------------------------------------------------------------


def _setup3(client, token):
    """Create one product and three ingredients, return (prod_id, [ing_id1, ing_id2, ing_id3])."""
    prod = client.post(
        "/products", json={"name": "Lasagna", "price": 15.0}, headers=_auth(token)
    ).json()
    ings = []
    for name, unit in [("Pasta Sheet", "kg"), ("Béchamel", "L"), ("Beef Mince", "kg")]:
        ing = client.post(
            "/inventory",
            json={"name": name, "qty": 10.0, "unit": unit, "price": 2.0},
            headers=_auth(token),
        ).json()
        ings.append(ing["id"])
    return prod["id"], ings


def test_set_recipe_creates_3_items(client):
    """PUT /recipes/product/{id} with 3 items returns 3 RecipeOut rows."""
    token = _login(client)
    prod_id, ing_ids = _setup3(client, token)
    payload = {
        "items": [
            {"ingredient_id": ing_ids[0], "qty": 0.1},
            {"ingredient_id": ing_ids[1], "qty": 0.05},
            {"ingredient_id": ing_ids[2], "qty": 0.2},
        ]
    }
    resp = client.put(f"/recipes/product/{prod_id}", json=payload, headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    ingredient_ids_out = {r["ingredient_id"] for r in data}
    assert ingredient_ids_out == set(ing_ids)
    for row in data:
        assert row["product_id"] == prod_id
        assert "ingredient_name" in row
        assert "product_name" in row
        assert row["qty"] > 0


def test_set_recipe_get_returns_same_3(client):
    """After PUT, GET /recipes?product_id= returns same 3 rows with correct names and qty."""
    token = _login(client)
    prod_id, ing_ids = _setup3(client, token)
    qtys = [0.1, 0.05, 0.2]
    payload = {
        "items": [
            {"ingredient_id": ing_ids[i], "qty": qtys[i]} for i in range(3)
        ]
    }
    client.put(f"/recipes/product/{prod_id}", json=payload, headers=_auth(token))

    resp = client.get(f"/recipes?product_id={prod_id}", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    by_ing = {r["ingredient_id"]: r for r in data}
    assert by_ing[ing_ids[0]]["qty"] == qtys[0]
    assert by_ing[ing_ids[1]]["qty"] == qtys[1]
    assert by_ing[ing_ids[2]]["qty"] == qtys[2]
    # names are populated
    for row in data:
        assert row["ingredient_name"] != ""
        assert row["product_name"] != ""


def test_set_recipe_replace_existing(client):
    """PUT with 2 items on a product that had 3 → only those 2 remain."""
    token = _login(client)
    prod_id, ing_ids = _setup3(client, token)
    # First set: 3 items
    client.put(
        f"/recipes/product/{prod_id}",
        json={"items": [{"ingredient_id": iid, "qty": 0.1} for iid in ing_ids]},
        headers=_auth(token),
    )
    # Replace with only first 2
    resp = client.put(
        f"/recipes/product/{prod_id}",
        json={"items": [{"ingredient_id": ing_ids[0], "qty": 0.3}, {"ingredient_id": ing_ids[1], "qty": 0.4}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # GET confirms exactly 2
    get_resp = client.get(f"/recipes?product_id={prod_id}", headers=_auth(token))
    assert len(get_resp.json()) == 2
    ingredient_ids_out = {r["ingredient_id"] for r in get_resp.json()}
    assert ingredient_ids_out == {ing_ids[0], ing_ids[1]}


def test_set_recipe_empty_items_clears_recipe(client):
    """PUT with empty items list clears the product's recipe."""
    token = _login(client)
    prod_id, ing_ids = _setup3(client, token)
    # Seed a recipe
    client.put(
        f"/recipes/product/{prod_id}",
        json={"items": [{"ingredient_id": ing_ids[0], "qty": 0.1}]},
        headers=_auth(token),
    )
    # Clear it
    resp = client.put(f"/recipes/product/{prod_id}", json={"items": []}, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []

    get_resp = client.get(f"/recipes?product_id={prod_id}", headers=_auth(token))
    assert get_resp.json() == []


def test_set_recipe_unknown_product_returns_404(client):
    """PUT with non-existent product_id returns 404."""
    token = _login(client)
    resp = client.put("/recipes/product/9999", json={"items": []}, headers=_auth(token))
    assert resp.status_code == 404
    assert "Product not found" in resp.json()["detail"]


def test_set_recipe_unknown_ingredient_returns_404(client):
    """PUT with a non-existent ingredient_id returns 404."""
    token = _login(client)
    prod = client.post("/products", json={"name": "Soup", "price": 5.0}, headers=_auth(token)).json()
    resp = client.put(
        f"/recipes/product/{prod['id']}",
        json={"items": [{"ingredient_id": 9999, "qty": 0.1}]},
        headers=_auth(token),
    )
    assert resp.status_code == 404
    assert "9999" in resp.json()["detail"]


def test_set_recipe_qty_zero_returns_400(client):
    """PUT with qty == 0 returns 400."""
    token = _login(client)
    prod_id, ing_ids = _setup3(client, token)
    resp = client.put(
        f"/recipes/product/{prod_id}",
        json={"items": [{"ingredient_id": ing_ids[0], "qty": 0.0}]},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "Quantity" in resp.json()["detail"]


def test_set_recipe_qty_negative_returns_400(client):
    """PUT with qty < 0 returns 400."""
    token = _login(client)
    prod_id, ing_ids = _setup3(client, token)
    resp = client.put(
        f"/recipes/product/{prod_id}",
        json={"items": [{"ingredient_id": ing_ids[0], "qty": -1.0}]},
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "Quantity" in resp.json()["detail"]


def test_set_recipe_duplicate_ingredient_returns_400(client):
    """PUT with duplicate ingredient_id in payload returns 400."""
    token = _login(client)
    prod_id, ing_ids = _setup3(client, token)
    resp = client.put(
        f"/recipes/product/{prod_id}",
        json={
            "items": [
                {"ingredient_id": ing_ids[0], "qty": 0.1},
                {"ingredient_id": ing_ids[0], "qty": 0.2},
            ]
        },
        headers=_auth(token),
    )
    assert resp.status_code == 400
    assert "Duplicate" in resp.json()["detail"]


def test_set_recipe_manager_allowed(client):
    """A manager token can call PUT /recipes/product/{id}."""
    admin_token = _login(client)
    # Create manager user
    client.post(
        "/users",
        json={"username": "mgr1", "password": "pass", "role": "manager"},
        headers=_auth(admin_token),
    )
    mgr_token = client.post("/auth/login", json={"username": "mgr1", "password": "pass"}).json()["access_token"]

    prod = client.post("/products", json={"name": "Salad", "price": 7.0}, headers=_auth(admin_token)).json()
    ing = client.post(
        "/inventory",
        json={"name": "Lettuce", "qty": 5.0, "unit": "kg", "price": 1.0},
        headers=_auth(admin_token),
    ).json()

    resp = client.put(
        f"/recipes/product/{prod['id']}",
        json={"items": [{"ingredient_id": ing["id"], "qty": 0.05}]},
        headers=_auth(mgr_token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_set_recipe_salesman_returns_403(client):
    """A salesman token is forbidden from PUT /recipes/product/{id}."""
    admin_token = _login(client)
    # Create salesman user
    client.post(
        "/users",
        json={"username": "sal1", "password": "pass", "role": "salesman"},
        headers=_auth(admin_token),
    )
    sal_token = client.post("/auth/login", json={"username": "sal1", "password": "pass"}).json()["access_token"]

    prod = client.post("/products", json={"name": "Burger", "price": 9.0}, headers=_auth(admin_token)).json()

    resp = client.put(
        f"/recipes/product/{prod['id']}",
        json={"items": []},
        headers=_auth(sal_token),
    )
    assert resp.status_code == 403
