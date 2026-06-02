"""
Tests for app.migrate_legacy – Phase 8 legacy-data migration.

Creates a temporary legacy SQLite DB (old format), runs migrate(), and asserts
that the new DB reflects the expected data.
"""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.migrate_legacy import migrate
from app.models import Customer, Inventory, Product, Recipe, Sale, SaleItem, User
from app.security import verify_password


# ------------------------------------------------------------------ #
# Helpers                                                               #
# ------------------------------------------------------------------ #

SALE_DATE_A = "2024-01-15 10:30:00"
SALE_DATE_B = "2024-01-16 11:00:00"


def _build_legacy_db(path: Path) -> str:
    """Create a legacy-format SQLite DB at *path* and return its str path."""
    conn = sqlite3.connect(str(path))
    c = conn.cursor()

    # users table (plaintext password)
    c.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )
    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("boss", "secret", "manager"),
    )

    # customers
    c.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            discount REAL DEFAULT 0
        )
        """
    )
    c.execute("INSERT INTO customers (name, discount) VALUES (?, ?)", ("alice", 5.0))

    # inventory (no reorder_level column)
    c.execute(
        """
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            qty REAL NOT NULL,
            unit TEXT,
            total_value REAL NOT NULL DEFAULT 0
        )
        """
    )
    c.execute(
        "INSERT INTO inventory (name, qty, unit, total_value) VALUES (?, ?, ?, ?)",
        ("flour", 50.0, "kg", 100.0),
    )

    # products
    c.execute(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            price REAL
        )
        """
    )
    c.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("bread", 5.0))
    c.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("cake", 8.0))

    # recipes: one valid (bread/flour) + one with unresolvable ingredient
    c.execute(
        """
        CREATE TABLE recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            ingredient TEXT,
            qty REAL
        )
        """
    )
    c.execute(
        "INSERT INTO recipes (product, ingredient, qty) VALUES (?, ?, ?)",
        ("bread", "flour", 2.0),
    )
    c.execute(
        # ingredient 'ghost_ingredient' does not exist in inventory → should be SKIPPED
        "INSERT INTO recipes (product, ingredient, qty) VALUES (?, ?, ?)",
        ("bread", "ghost_ingredient", 1.0),
    )

    # sales: flat rows
    # Group A (same date/customer/payment_status) → 1 Sale with 2 SaleItems
    c.execute(
        """
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT,
            qty REAL,
            total REAL,
            date TEXT,
            customer TEXT,
            payment_status TEXT
        )
        """
    )
    # Group A – alice, Unpaid
    c.execute(
        "INSERT INTO sales (product, qty, total, date, customer, payment_status)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ("bread", 3.0, 15.0, SALE_DATE_A, "alice", "Unpaid"),
    )
    c.execute(
        "INSERT INTO sales (product, qty, total, date, customer, payment_status)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ("cake", 2.0, 16.0, SALE_DATE_A, "alice", "Unpaid"),
    )
    # Group B – walk-in (no customer), Paid
    c.execute(
        "INSERT INTO sales (product, qty, total, date, customer, payment_status)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ("bread", 1.0, 5.0, SALE_DATE_B, "", "Paid"),
    )

    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture()
def legacy_db(tmp_path):
    return _build_legacy_db(tmp_path / "legacy.db")


@pytest.fixture()
def new_session(tmp_path):
    """Yield a SQLAlchemy session backed by a fresh new-schema DB."""
    db_path = tmp_path / "new.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


# ------------------------------------------------------------------ #
# Tests                                                                 #
# ------------------------------------------------------------------ #


def test_users_migrated_with_hashed_password(legacy_db, new_session):
    summary = migrate(legacy_db, new_session)

    user = new_session.query(User).filter(User.username == "boss").first()
    assert user is not None, "User 'boss' should be created"
    assert user.role == "manager"
    # Password must NOT be stored as plaintext
    assert user.password_hash != "secret", "Password should be hashed, not stored plaintext"
    # verify_password must succeed with the original plaintext
    assert verify_password("secret", user.password_hash), "verify_password should return True"

    assert summary["users"]["created"] == 1


def test_customer_migrated(legacy_db, new_session):
    migrate(legacy_db, new_session)

    alice = new_session.query(Customer).filter(Customer.name == "alice").first()
    assert alice is not None
    assert alice.discount == 5.0


def test_inventory_migrated_with_reorder_zero(legacy_db, new_session):
    migrate(legacy_db, new_session)

    flour = new_session.query(Inventory).filter(Inventory.name == "flour").first()
    assert flour is not None
    assert flour.qty == 50.0
    assert flour.unit == "kg"
    assert flour.total_value == 100.0
    assert flour.reorder_level == 0.0, "reorder_level should default to 0 for legacy rows"


def test_product_migrated(legacy_db, new_session):
    migrate(legacy_db, new_session)

    bread = new_session.query(Product).filter(Product.name == "bread").first()
    assert bread is not None
    assert bread.price == 5.0


def test_recipe_resolved_to_fk_ids(legacy_db, new_session):
    migrate(legacy_db, new_session)

    bread = new_session.query(Product).filter(Product.name == "bread").first()
    flour = new_session.query(Inventory).filter(Inventory.name == "flour").first()

    recipe = (
        new_session.query(Recipe)
        .filter(Recipe.product_id == bread.id, Recipe.ingredient_id == flour.id)
        .first()
    )
    assert recipe is not None, "Recipe bread/flour should be migrated with correct FK ids"
    assert recipe.qty == 2.0


def test_recipe_with_unresolvable_ingredient_is_skipped(legacy_db, new_session):
    summary = migrate(legacy_db, new_session)

    # Only the valid recipe (bread/flour) should be created
    recipes = new_session.query(Recipe).all()
    assert len(recipes) == 1, "Only 1 valid recipe should exist"
    assert summary["recipes"]["created"] == 1
    assert summary["recipes"]["skipped"] == 1, "The ghost_ingredient recipe should be skipped"


def test_sales_grouped_correctly(legacy_db, new_session):
    migrate(legacy_db, new_session)

    sales = new_session.query(Sale).all()
    # Group A (alice/Unpaid) + Group B (walk-in/Paid) = 2 sales
    assert len(sales) == 2

    # Find the alice Unpaid sale
    alice_sale = next(
        (s for s in sales if s.payment_status == "Unpaid"),
        None,
    )
    assert alice_sale is not None, "Alice's Unpaid sale should exist"
    # Subtotal = 15 + 16 = 31
    assert alice_sale.subtotal == pytest.approx(31.0)
    assert alice_sale.total == pytest.approx(31.0)
    assert alice_sale.discount_pct == 0.0
    assert alice_sale.discount_amount == 0.0

    # Customer should be linked to alice
    alice = new_session.query(Customer).filter(Customer.name == "alice").first()
    assert alice_sale.customer_id == alice.id


def test_sale_items_created(legacy_db, new_session):
    migrate(legacy_db, new_session)

    alice_sale = (
        new_session.query(Sale).filter(Sale.payment_status == "Unpaid").first()
    )
    items = new_session.query(SaleItem).filter(SaleItem.sale_id == alice_sale.id).all()
    assert len(items) == 2, "Alice's sale should have 2 SaleItems"

    names = {item.product_name for item in items}
    assert "bread" in names
    assert "cake" in names

    bread_item = next(i for i in items if i.product_name == "bread")
    assert bread_item.qty == 3.0
    assert bread_item.line_total == pytest.approx(15.0)
    assert bread_item.unit_price == pytest.approx(5.0)

    # product_id should be resolved to the actual bread Product
    bread_product = new_session.query(Product).filter(Product.name == "bread").first()
    assert bread_item.product_id == bread_product.id


def test_walk_in_sale_has_no_customer(legacy_db, new_session):
    migrate(legacy_db, new_session)

    paid_sale = (
        new_session.query(Sale).filter(Sale.payment_status == "Paid").first()
    )
    assert paid_sale is not None
    assert paid_sale.customer_id is None
    assert paid_sale.subtotal == pytest.approx(5.0)

    items = new_session.query(SaleItem).filter(SaleItem.sale_id == paid_sale.id).all()
    assert len(items) == 1


def test_summary_counts(legacy_db, new_session):
    summary = migrate(legacy_db, new_session)

    assert summary["users"]["created"] == 1
    assert summary["customers"]["created"] == 1
    assert summary["inventory"]["created"] == 1
    assert summary["products"]["created"] == 2
    assert summary["recipes"]["created"] == 1
    assert summary["recipes"]["skipped"] == 1
    assert summary["sales"]["created"] == 2
    assert summary["sale_items"]["created"] == 3  # 2 from alice + 1 walk-in


def test_idempotent_users(legacy_db, new_session):
    """Running migrate twice should not create duplicate users."""
    migrate(legacy_db, new_session)
    new_session.flush()
    summary2 = migrate(legacy_db, new_session)
    assert summary2["users"]["created"] == 0
    count = new_session.query(User).filter(User.username == "boss").count()
    assert count == 1


def test_idempotent_inventory(legacy_db, new_session):
    """Running migrate twice should not create duplicate inventory items."""
    migrate(legacy_db, new_session)
    new_session.flush()
    summary2 = migrate(legacy_db, new_session)
    assert summary2["inventory"]["created"] == 0
    count = new_session.query(Inventory).filter(Inventory.name == "flour").count()
    assert count == 1


def test_missing_table_handled_gracefully(tmp_path, new_session):
    """A legacy DB missing a table entirely should not crash migrate()."""
    # Build a minimal legacy DB with only the users table
    db_path = tmp_path / "partial_legacy.db"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
        """
    )
    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin2", "pass2", "admin"),
    )
    conn.commit()
    conn.close()

    # Should not raise even though customers/inventory/products/recipes/sales are absent
    summary = migrate(str(db_path), new_session)
    assert summary["users"]["created"] == 1
    # Other tables got skipped without crashing
    assert "skipped_table" in summary["customers"] or summary["customers"]["created"] == 0
