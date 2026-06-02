"""Reporting service: date-range resolution and report computation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date as date_type

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Customer, Inventory, Recipe, Sale, SaleItem


def resolve_range(type_: str, start: str | None, end: str | None) -> dict:
    """Return dict with keys: start (datetime), end (datetime), label (str)."""
    if start is not None and end is not None:
        try:
            s = date_type.fromisoformat(start)
            e = date_type.fromisoformat(end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")
        return {
            "start": datetime(s.year, s.month, s.day, 0, 0, 0),
            "end": datetime(e.year, e.month, e.day, 23, 59, 59, 999999),
            "label": "Custom",
        }

    if start is not None or end is not None:
        # Only one of them is given — validate the one that was given
        try:
            if start is not None:
                date_type.fromisoformat(start)
            if end is not None:
                date_type.fromisoformat(end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")

    now = datetime.now()
    type_ = type_ or "Daily"

    if type_ == "Daily":
        s = datetime(now.year, now.month, now.day, 0, 0, 0)
        e = datetime(now.year, now.month, now.day, 23, 59, 59, 999999)
        label = "Daily"
    elif type_ == "Weekly":
        from datetime import timedelta
        s = now - timedelta(days=7)
        e = now
        label = "Weekly"
    elif type_ == "Monthly":
        s = datetime(now.year, now.month, 1, 0, 0, 0)
        # Last day of current month
        if now.month == 12:
            e = datetime(now.year + 1, 1, 1, 0, 0, 0)
        else:
            e = datetime(now.year, now.month + 1, 1, 0, 0, 0)
        # Subtract 1 microsecond to stay within the month
        from datetime import timedelta as td
        e = e - td(microseconds=1)
        label = "Monthly"
    elif type_ == "Yearly":
        s = datetime(now.year, 1, 1, 0, 0, 0)
        e = datetime(now.year, 12, 31, 23, 59, 59, 999999)
        label = "Yearly"
    else:
        # Default to Daily for unknown types
        s = datetime(now.year, now.month, now.day, 0, 0, 0)
        e = datetime(now.year, now.month, now.day, 23, 59, 59, 999999)
        label = "Daily"

    return {"start": s, "end": e, "label": label}


def build_report(db: Session, type_: str, start: str | None, end: str | None) -> dict:
    """Compute and return the full report as a plain dict."""
    rng = resolve_range(type_, start, end)
    range_start: datetime = rng["start"]
    range_end: datetime = rng["end"]
    label: str = rng["label"]

    # Fetch all sales in range
    sales = (
        db.query(Sale)
        .filter(Sale.created_at >= range_start, Sale.created_at <= range_end)
        .all()
    )

    sale_ids = [s.id for s in sales]

    # Fetch all sale items for those sales
    if sale_ids:
        sale_items = db.query(SaleItem).filter(SaleItem.sale_id.in_(sale_ids)).all()
    else:
        sale_items = []

    # Map sale_id -> Sale for quick lookup
    sale_map = {s.id: s for s in sales}

    # Map customer_id -> Customer for quick lookup
    customer_ids = {s.customer_id for s in sales if s.customer_id is not None}
    if customer_ids:
        customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
        customer_map = {c.id: c for c in customers}
    else:
        customer_map = {}

    # ----------------------------------------------------------------
    # Overview
    # ----------------------------------------------------------------
    sales_count = len(sales)
    paid_revenue = sum(s.total for s in sales if s.payment_status == "Paid")
    unpaid_debt = sum(s.total for s in sales if s.payment_status == "Unpaid")
    grand_total = paid_revenue + unpaid_debt

    # ----------------------------------------------------------------
    # Sales details (one row per SaleItem)
    # ----------------------------------------------------------------
    sales_details = []
    for item in sale_items:
        sale = sale_map.get(item.sale_id)
        if sale is None:
            continue
        cust = customer_map.get(sale.customer_id) if sale.customer_id else None
        sales_details.append({
            "sale_id": item.sale_id,
            "date": sale.created_at.isoformat(),
            "product": item.product_name,
            "qty": item.qty,
            "line_total": item.line_total,
            "customer": cust.name if cust else "",
            "payment_status": sale.payment_status,
        })

    # ----------------------------------------------------------------
    # Inventory consumption
    # ----------------------------------------------------------------
    # Aggregate consumed per ingredient_id across all sale items in range
    ingredient_consumed: dict[int, float] = defaultdict(float)
    if sale_ids:
        # Get all product_ids that appear in these sale items
        product_ids = {item.product_id for item in sale_items}
        # Fetch all relevant recipes
        recipes = (
            db.query(Recipe)
            .filter(Recipe.product_id.in_(product_ids))
            .all()
        )
        # Build product_id -> list[(ingredient_id, recipe_qty)]
        product_recipes: dict[int, list[tuple[int, float]]] = defaultdict(list)
        for r in recipes:
            product_recipes[r.product_id].append((r.ingredient_id, r.qty))

        # Accumulate consumption
        for item in sale_items:
            for ing_id, recipe_qty in product_recipes.get(item.product_id, []):
                ingredient_consumed[ing_id] += recipe_qty * item.qty

    # Fetch inventory for the consumed ingredients
    inventory_consumption = []
    if ingredient_consumed:
        ing_ids = list(ingredient_consumed.keys())
        inv_items = db.query(Inventory).filter(Inventory.id.in_(ing_ids)).all()
        inv_map = {i.id: i for i in inv_items}
        for ing_id, consumed in ingredient_consumed.items():
            inv = inv_map.get(ing_id)
            inventory_consumption.append({
                "ingredient": inv.name if inv else str(ing_id),
                "consumed": consumed,
                "remaining": inv.qty if inv else 0.0,
                "unit": inv.unit if inv else "",
            })

    # ----------------------------------------------------------------
    # Current inventory
    # ----------------------------------------------------------------
    all_inventory = db.query(Inventory).order_by(Inventory.name).all()
    current_inventory = [
        {"name": i.name, "qty": i.qty, "unit": i.unit}
        for i in all_inventory
    ]

    # ----------------------------------------------------------------
    # Customer summary
    # ----------------------------------------------------------------
    customer_purchases: dict[int, dict] = {}
    for sale in sales:
        if sale.customer_id is None:
            continue
        cust = customer_map.get(sale.customer_id)
        if cust is None:
            continue
        if sale.customer_id not in customer_purchases:
            customer_purchases[sale.customer_id] = {
                "customer": cust.name,
                "purchases": 0,
                "paid": 0.0,
                "debt": 0.0,
            }
        entry = customer_purchases[sale.customer_id]
        entry["purchases"] += 1
        if sale.payment_status == "Paid":
            entry["paid"] += sale.total
        else:
            entry["debt"] += sale.total

    customer_summary = sorted(customer_purchases.values(), key=lambda x: x["customer"])

    # ----------------------------------------------------------------
    # Unpaid bills
    # ----------------------------------------------------------------
    unpaid_bills = []
    for sale in sales:
        if sale.payment_status != "Unpaid":
            continue
        cust = customer_map.get(sale.customer_id) if sale.customer_id else None
        unpaid_bills.append({
            "sale_id": sale.id,
            "date": sale.created_at.isoformat(),
            "customer": cust.name if cust else "",
            "total": sale.total,
        })

    return {
        "range": {
            "start": range_start.isoformat(),
            "end": range_end.isoformat(),
            "label": label,
        },
        "overview": {
            "sales_count": sales_count,
            "paid_revenue": paid_revenue,
            "unpaid_debt": unpaid_debt,
            "grand_total": grand_total,
        },
        "sales_details": sales_details,
        "inventory_consumption": inventory_consumption,
        "current_inventory": current_inventory,
        "customer_summary": customer_summary,
        "unpaid_bills": unpaid_bills,
    }
