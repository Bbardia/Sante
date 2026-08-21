"""
migrate_legacy.py – Phase 8 legacy-data migration for Santé POS.

Usage (CLI):
    python -m app.migrate_legacy <path/to/old/database.db>

The CLI opens a SessionLocal() against the current new DB (backend/database.db)
and runs migrate(), printing a summary dict.

The migrate() function can also be called directly from tests with any Session.
"""

import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

from app.db import SessionLocal
from app.models import Customer, Inventory, Product, Recipe, Sale, SaleItem, User
from app.security import hash_password


def _parse_date(raw: str) -> datetime:
    """Parse a legacy date string, falling back gracefully."""
    if not raw:
        return datetime.now()
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    return datetime.now()


def migrate(old_db_path: str, session) -> dict:
    """
    Read the legacy SQLite at old_db_path and write into the new DB via session.

    The caller is responsible for committing (or rolling back) after this call.
    The CLI wrapper below commits automatically.

    Returns a summary dict, e.g.:
        {
            "users": {"created": 2},
            "customers": {"created": 3},
            "inventory": {"created": 10},
            "products": {"created": 5},
            "recipes": {"created": 4, "skipped": 1},
            "sales": {"created": 2},
            "sale_items": {"created": 5},
        }
    """
    conn = sqlite3.connect(old_db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    summary: dict = {
        "users": {"created": 0},
        "customers": {"created": 0},
        "inventory": {"created": 0},
        "products": {"created": 0},
        "recipes": {"created": 0, "skipped": 0},
        "sales": {"created": 0},
        "sale_items": {"created": 0},
    }

    # ------------------------------------------------------------------ #
    # 1. Users                                                              #
    # ------------------------------------------------------------------ #
    try:
        cur.execute("SELECT username, password, role FROM users")
        for row in cur.fetchall():
            username = row["username"]
            existing = session.query(User).filter(User.username == username).first()
            if existing is None:
                session.add(
                    User(
                        username=username,
                        password_hash=hash_password(row["password"]),
                        role=row["role"],
                    )
                )
                summary["users"]["created"] += 1
    except sqlite3.OperationalError:
        summary["users"]["skipped_table"] = True
    session.flush()  # ensure PKs are assigned before later lookups

    # ------------------------------------------------------------------ #
    # 2. Customers                                                          #
    # ------------------------------------------------------------------ #
    try:
        cur.execute("SELECT name, discount FROM customers")
        for row in cur.fetchall():
            name = row["name"]
            if not name:
                continue
            existing = session.query(Customer).filter(Customer.name == name).first()
            if existing is None:
                session.add(Customer(name=name, discount=row["discount"] or 0.0))
                summary["customers"]["created"] += 1
    except sqlite3.OperationalError:
        summary["customers"]["skipped_table"] = True
    session.flush()

    # ------------------------------------------------------------------ #
    # 3. Inventory                                                          #
    # ------------------------------------------------------------------ #
    try:
        cur.execute("SELECT name, qty, unit, total_value FROM inventory")
        for row in cur.fetchall():
            name = row["name"]
            if not name:
                continue
            existing = session.query(Inventory).filter(Inventory.name == name).first()
            if existing is None:
                session.add(
                    Inventory(
                        name=name,
                        qty=row["qty"] or 0.0,
                        unit=row["unit"] or "",
                        total_value=row["total_value"] or 0.0,
                        reorder_level=0.0,  # legacy had no reorder_level
                    )
                )
                summary["inventory"]["created"] += 1
    except sqlite3.OperationalError:
        summary["inventory"]["skipped_table"] = True
    session.flush()

    # ------------------------------------------------------------------ #
    # 4. Products                                                           #
    # ------------------------------------------------------------------ #
    try:
        cur.execute("SELECT name, price FROM products")
        for row in cur.fetchall():
            name = row["name"]
            if not name:
                continue
            existing = session.query(Product).filter(Product.name == name).first()
            if existing is None:
                session.add(Product(name=name, price=row["price"] or 0.0))
                summary["products"]["created"] += 1
    except sqlite3.OperationalError:
        summary["products"]["skipped_table"] = True
    session.flush()

    # ------------------------------------------------------------------ #
    # 5. Recipes (text names → FK ids, case-insensitive)                   #
    # ------------------------------------------------------------------ #
    try:
        cur.execute("SELECT product, ingredient, qty FROM recipes")

        # Build case-insensitive lookup maps from the NEW DB (post-flush)
        all_products = session.query(Product).all()
        product_map = {p.name.lower(): p.id for p in all_products}

        all_inventory = session.query(Inventory).all()
        inventory_map = {i.name.lower(): i.id for i in all_inventory}

        for row in cur.fetchall():
            prod_name = (row["product"] or "").lower().strip()
            ing_name = (row["ingredient"] or "").lower().strip()

            pid = product_map.get(prod_name)
            iid = inventory_map.get(ing_name)

            if pid is None or iid is None:
                summary["recipes"]["skipped"] += 1
                continue

            session.add(Recipe(product_id=pid, ingredient_id=iid, qty=row["qty"] or 0.0))
            summary["recipes"]["created"] += 1
    except sqlite3.OperationalError:
        summary["recipes"]["skipped_table"] = True
    session.flush()

    # ------------------------------------------------------------------ #
    # 6. Sales – group flat rows by (date, customer, payment_status)       #
    # ------------------------------------------------------------------ #
    try:
        cur.execute(
            "SELECT product, qty, total, date, customer, payment_status FROM sales"
        )
        raw_sales = cur.fetchall()

        # Build product lookup for SaleItems
        all_products2 = session.query(Product).all()
        product_map2 = {p.name.lower(): p.id for p in all_products2}

        # Build customer lookup
        all_customers = session.query(Customer).all()
        customer_map = {c.name.lower(): c.id for c in all_customers}

        # Group by (date_str, customer, payment_status)
        groups: dict = defaultdict(list)
        for row in raw_sales:
            key = (
                row["date"] or "",
                row["customer"] or "",
                row["payment_status"] or "Paid",
            )
            groups[key].append(row)

        for (date_str, customer_name, payment_status), rows in groups.items():
            # Resolve customer
            customer_id = None
            if customer_name:
                cust_name_lower = customer_name.lower()
                if cust_name_lower in customer_map:
                    customer_id = customer_map[cust_name_lower]
                else:
                    # Customer referenced in sales but not in customers table –
                    # create them on the fly with 0 discount.
                    new_cust = Customer(name=customer_name, discount=0.0)
                    session.add(new_cust)
                    session.flush()
                    customer_map[cust_name_lower] = new_cust.id
                    customer_id = new_cust.id

            subtotal = sum((r["total"] or 0.0) for r in rows)
            created_at = _parse_date(date_str)
            payment_status_val = payment_status if payment_status else "Paid"

            sale = Sale(
                created_at=created_at,
                customer_id=customer_id,
                subtotal=subtotal,
                discount_pct=0.0,
                discount_amount=0.0,
                total=subtotal,
                payment_status=payment_status_val,
            )
            session.add(sale)
            session.flush()  # get sale.id
            summary["sales"]["created"] += 1

            for r in rows:
                prod_name_raw = r["product"] or ""
                prod_id = product_map2.get(prod_name_raw.lower())
                # If product not found, set product_id=0.
                # SaleItem.product_id is a non-nullable int FK; storing 0 is a
                # sentinel meaning "unknown/deleted product" since there is no
                # product with id=0 in SQLite autoincrement tables.
                qty = r["qty"] or 0.0
                total = r["total"] or 0.0
                unit_price = (total / qty) if qty else 0.0

                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=prod_id if prod_id is not None else 0,
                    product_name=prod_name_raw,
                    qty=qty,
                    unit_price=unit_price,
                    line_total=total,
                )
                session.add(sale_item)
                summary["sale_items"]["created"] += 1

        session.flush()

    except sqlite3.OperationalError:
        summary["sales"]["skipped_table"] = True

    conn.close()
    return summary


# ------------------------------------------------------------------ #
# CLI entrypoint                                                        #
# ------------------------------------------------------------------ #
def _cli():
    if len(sys.argv) < 2:
        print("Usage: python -m app.migrate_legacy <path/to/old/database.db>")
        sys.exit(1)

    old_db_path = sys.argv[1]

    # Import models to ensure all tables are registered with Base before any
    # session-level operations (models are registered on import as a side-effect).
    import app.models  # noqa: F401

    from app.db import engine
    from app.db import Base as AppBase

    AppBase.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        summary = migrate(old_db_path, session)
        session.commit()
        print("Migration complete.")
        print(summary)
    except Exception as exc:
        session.rollback()
        print(f"Migration FAILED: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    _cli()
