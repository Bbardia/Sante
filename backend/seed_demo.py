"""
seed_demo.py — Reset and seed the Santé dev database with realistic demo data.

Usage:
    cd backend && .venv/bin/python seed_demo.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Bootstrap: make sure 'app' is importable when run from backend/
# ---------------------------------------------------------------------------
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.db import Base, engine, SessionLocal
from app.models import (
    Customer,
    Inventory,
    Product,
    Recipe,
    Sale,
    SaleItem,
    User,
)
from app.schemas import CartItem, CheckoutRequest
from app.security import hash_password
from app.services.checkout import perform_checkout

# ---------------------------------------------------------------------------
# 1. Clean slate
# ---------------------------------------------------------------------------
print("Dropping and recreating all tables …")
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

db = SessionLocal()

# ---------------------------------------------------------------------------
# 2. Users
# ---------------------------------------------------------------------------
users_data = [
    ("admin",   "admin",   "admin"),
    ("manager", "manager", "manager"),
    ("sara",    "sara",    "salesman"),
    ("stock",   "stock",   "stockman"),
]
for username, password, role in users_data:
    db.add(User(username=username, password_hash=hash_password(password), role=role))
db.flush()

# ---------------------------------------------------------------------------
# 3. Inventory (ingredients)
#    Strategy: keep qty high so demo sales succeed;
#    mark 3 items "low stock" by giving them a HIGH reorder_level.
# ---------------------------------------------------------------------------
ingredients_data = [
    # (name,          qty,    unit,  unit_price_t,  reorder_level)
    ("Coffee Beans",  5000,   "g",   2_000,          6_000),   # LOW  (rl > qty)
    ("Milk",          50,     "L",   25_000,         60),      # LOW  (rl > qty)
    ("Sugar",         10_000, "g",   500,            2_000),   # OK
    ("Flour",         20_000, "g",   300,            3_000),   # OK
    ("Chocolate",     8_000,  "g",   1_500,          10_000),  # LOW  (rl > qty)
    ("Paper Cups",    1_000,  "pcs", 1_000,          200),     # OK
]
inv_objs: dict[str, Inventory] = {}
for name, qty, unit, unit_price_t, reorder_level in ingredients_data:
    obj = Inventory(
        name=name,
        qty=qty,
        unit=unit,
        total_value=qty * unit_price_t,
        reorder_level=reorder_level,
    )
    db.add(obj)
    inv_objs[name] = obj
db.flush()

# ---------------------------------------------------------------------------
# 4. Products
# ---------------------------------------------------------------------------
products_data = [
    ("Espresso",        45_000),
    ("Cappuccino",      65_000),
    ("Latte",           70_000),
    ("Croissant",       55_000),
    ("Chocolate Cake",  80_000),
]
prod_objs: dict[str, Product] = {}
for name, price in products_data:
    obj = Product(name=name, price=price)
    db.add(obj)
    prod_objs[name] = obj
db.flush()

# ---------------------------------------------------------------------------
# 5. Recipes
# ---------------------------------------------------------------------------
recipes_raw = [
    # (product_name,     ingredient_name,  qty_per_unit)
    ("Espresso",         "Coffee Beans",   18),   # 18 g per shot
    ("Espresso",         "Paper Cups",     1),
    ("Cappuccino",       "Coffee Beans",   18),
    ("Cappuccino",       "Milk",           0.15), # 150 ml → 0.15 L
    ("Cappuccino",       "Paper Cups",     1),
    ("Latte",            "Coffee Beans",   18),
    ("Latte",            "Milk",           0.25),
    ("Latte",            "Paper Cups",     1),
    ("Croissant",        "Flour",          120),  # 120 g per croissant
    ("Croissant",        "Sugar",          20),
    ("Chocolate Cake",   "Flour",          200),
    ("Chocolate Cake",   "Sugar",          80),
    ("Chocolate Cake",   "Chocolate",      150),
]
for prod_name, ing_name, qty in recipes_raw:
    db.add(
        Recipe(
            product_id=prod_objs[prod_name].id,
            ingredient_id=inv_objs[ing_name].id,
            qty=qty,
        )
    )
db.flush()

# ---------------------------------------------------------------------------
# 6. Customers
# ---------------------------------------------------------------------------
customers_data = [
    ("Ali Rezaei",    10),
    ("Sara Mohammadi", 5),
    ("Walk-in VIP",    0),
]
cust_objs: dict[str, Customer] = {}
for name, disc in customers_data:
    obj = Customer(name=name, discount=disc)
    db.add(obj)
    cust_objs[name] = obj
db.flush()

# ---------------------------------------------------------------------------
# 7a. Today's sales via perform_checkout
#     Keep per-item quantities small to stay well within stock.
# ---------------------------------------------------------------------------
ali = cust_objs["Ali Rezaei"]
sara_c = cust_objs["Sara Mohammadi"]
esp   = prod_objs["Espresso"]
cap   = prod_objs["Cappuccino"]
lat   = prod_objs["Latte"]
croi  = prod_objs["Croissant"]
cake  = prod_objs["Chocolate Cake"]

today_checkouts = [
    # Walk-in, no customer, paid
    CheckoutRequest(items=[CartItem(product_id=esp.id, qty=2)]),
    # Walk-in, no customer, paid
    CheckoutRequest(items=[CartItem(product_id=cap.id, qty=1),
                            CartItem(product_id=croi.id, qty=1)]),
    # Customer Ali, no extra discount, paid
    CheckoutRequest(customer_id=ali.id, discount_pct=ali.discount,
                    items=[CartItem(product_id=lat.id, qty=2)]),
    # Customer Sara, paid
    CheckoutRequest(customer_id=sara_c.id, discount_pct=sara_c.discount,
                    items=[CartItem(product_id=cake.id, qty=1)]),
    # Walk-in, paid
    CheckoutRequest(items=[CartItem(product_id=esp.id, qty=1),
                            CartItem(product_id=cake.id, qty=1)]),
    # PAY-LATER (debt) — Ali
    CheckoutRequest(customer_id=ali.id, discount_pct=ali.discount,
                    pay_later=True,
                    items=[CartItem(product_id=cap.id, qty=2),
                            CartItem(product_id=croi.id, qty=2)]),
    # PAY-LATER (debt) — Sara
    CheckoutRequest(customer_id=sara_c.id, discount_pct=sara_c.discount,
                    pay_later=True,
                    items=[CartItem(product_id=lat.id, qty=1),
                            CartItem(product_id=cake.id, qty=1)]),
    # Walk-in, paid
    CheckoutRequest(items=[CartItem(product_id=croi.id, qty=3)]),
]

today_receipts = []
for req in today_checkouts:
    receipt = perform_checkout(db, req)
    today_receipts.append(receipt)

# ---------------------------------------------------------------------------
# 7b. Backdated sales: manually insert Sale + SaleItem rows
#     and deduct inventory the same way checkout does.
# ---------------------------------------------------------------------------

def _avg_price(inv: Inventory) -> float:
    return inv.total_value / inv.qty if inv.qty > 0 else 0.0


def _deduct(inv: Inventory, qty_needed: float) -> None:
    avg = _avg_price(inv)
    inv.qty -= qty_needed
    inv.total_value = max(0.0, inv.total_value - qty_needed * avg)


def backdate_sale(
    days_ago: int,
    items: list[tuple[Product, float]],
    customer: Customer | None = None,
    discount_pct: float = 0.0,
    pay_later: bool = False,
) -> Sale:
    """Create a historical sale directly, deducting inventory manually."""
    subtotal = sum(p.price * qty for p, qty in items)
    discount_amount = subtotal * discount_pct / 100
    total = subtotal - discount_amount
    payment_status = "Unpaid" if pay_later else "Paid"

    sale = Sale(
        created_at=datetime.now() - timedelta(days=days_ago),
        customer_id=customer.id if customer else None,
        subtotal=subtotal,
        discount_pct=discount_pct,
        discount_amount=discount_amount,
        total=total,
        payment_status=payment_status,
    )
    db.add(sale)
    db.flush()

    for product, qty in items:
        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                qty=qty,
                unit_price=product.price,
                line_total=product.price * qty,
            )
        )

    # Deduct ingredients for each product
    for product, qty in items:
        from sqlalchemy.orm import Session as _S
        recipes = db.query(Recipe).filter(Recipe.product_id == product.id).all()
        for r in recipes:
            inv = db.get(Inventory, r.ingredient_id)
            if inv is not None:
                _deduct(inv, r.qty * qty)

    db.flush()
    return sale


# 5 backdated sales across the last ~25 days
backdate_sale(3,  [(esp, 3), (croi, 2)])
backdate_sale(7,  [(cap, 2), (lat, 1)], customer=ali, discount_pct=ali.discount)
backdate_sale(12, [(cake, 2), (croi, 1)], customer=sara_c, discount_pct=sara_c.discount)
backdate_sale(18, [(esp, 4), (lat, 2)], pay_later=True)  # Unpaid walk-in (pay_later needs customer — use sara_c)
# Note: pay_later without customer is technically disallowed by checkout but OK when inserting directly
# Let's keep it realistic: assign customer to pay_later backdated ones
backdate_sale(18, [(cap, 3)], customer=ali, discount_pct=ali.discount, pay_later=True)
backdate_sale(25, [(esp, 2), (cake, 1), (croi, 3)])

db.commit()

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
from sqlalchemy import func

user_count = db.query(func.count(User.id)).scalar()
ing_count  = db.query(func.count(Inventory.id)).scalar()
prod_count = db.query(func.count(Product.id)).scalar()
rec_count  = db.query(func.count(Recipe.id)).scalar()
cust_count = db.query(func.count(Customer.id)).scalar()
paid_count = db.query(func.count(Sale.id)).filter(Sale.payment_status == "Paid").scalar()
unpaid_count = db.query(func.count(Sale.id)).filter(Sale.payment_status == "Unpaid").scalar()
total_sales = (paid_count or 0) + (unpaid_count or 0)

low_stock_items = (
    db.query(Inventory)
    .filter(Inventory.reorder_level > 0, Inventory.qty <= Inventory.reorder_level)
    .all()
)

db.close()

print()
print("=" * 56)
print("  Santé Demo Seed — Summary")
print("=" * 56)
print(f"  Users:        {user_count}")
print(f"  Ingredients:  {ing_count}  (low-stock: {len(low_stock_items)})")
for item in low_stock_items:
    print(f"                  • {item.name}: {item.qty} {item.unit} (reorder ≥ {item.reorder_level})")
print(f"  Products:     {prod_count}")
print(f"  Recipes:      {rec_count}")
print(f"  Customers:    {cust_count}")
print(f"  Sales total:  {total_sales}  (Paid: {paid_count}, Unpaid: {unpaid_count})")
print()
print("  Login credentials:")
for username, password, role in users_data:
    print(f"    {username:10s} / {password:10s}  [{role}]")
print("=" * 56)
print("Done.")
