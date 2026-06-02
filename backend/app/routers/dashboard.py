"""Dashboard router: high-level KPI snapshot."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Inventory, Sale, SaleItem
from app.security import require_roles

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_allowed = require_roles("admin", "manager", "salesman")


@router.get("")
def get_dashboard(
    db: Session = Depends(get_db),
    _=Depends(_allowed),
) -> dict:
    now = datetime.now()
    today = now.date()
    window_start = now - timedelta(days=30)

    # ---- today's revenue & sales_count --------------------------------
    today_sales = (
        db.query(func.sum(Sale.total), func.count(Sale.id))
        .filter(func.date(Sale.created_at) == today)
        .one()
    )
    revenue = today_sales[0] or 0.0
    sales_count = today_sales[1] or 0

    # ---- top 5 products over last 30 days (by summed qty DESC) --------
    top_rows = (
        db.query(SaleItem.product_name, func.sum(SaleItem.qty).label("total_qty"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.created_at >= window_start)
        .group_by(SaleItem.product_name)
        .order_by(func.sum(SaleItem.qty).desc())
        .limit(5)
        .all()
    )
    top_products = [{"product": row.product_name, "qty": row.total_qty} for row in top_rows]

    # ---- low stock: reorder_level > 0 AND qty <= reorder_level --------
    low_rows = (
        db.query(Inventory)
        .filter(Inventory.reorder_level > 0, Inventory.qty <= Inventory.reorder_level)
        .order_by(Inventory.name)
        .all()
    )
    low_stock = [
        {
            "name": item.name,
            "qty": item.qty,
            "unit": item.unit,
            "reorder_level": item.reorder_level,
        }
        for item in low_rows
    ]

    return {
        "today": {"revenue": revenue, "sales_count": sales_count},
        "top_products": top_products,
        "low_stock": low_stock,
    }
