from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Customer, Sale, SaleItem
from app.schemas import CheckoutRequest, ReceiptItem, ReceiptOut, SaleSummaryOut
from app.security import require_roles
from app.services.checkout import perform_checkout

router = APIRouter(prefix="/sales", tags=["sales"])

_allowed = require_roles("admin", "manager", "salesman")


@router.post("", response_model=ReceiptOut)
def create_sale(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    return perform_checkout(db, body)


@router.get("", response_model=list[SaleSummaryOut])
def list_sales(
    search: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    """Return sales history ordered by created_at DESC.

    Filters:
    - search: match customer name (contains) OR any SaleItem.product_name (contains), case-insensitive.
    - start/end: YYYY-MM-DD, inclusive date range on created_at.
    """
    from datetime import date as date_type

    # Parse date range
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None
    if start is not None:
        try:
            d = date_type.fromisoformat(start)
            start_dt = datetime(d.year, d.month, d.day, 0, 0, 0)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid start date '{start}'. Expected YYYY-MM-DD."
            )
    if end is not None:
        try:
            d = date_type.fromisoformat(end)
            end_dt = datetime(d.year, d.month, d.day, 23, 59, 59, 999999)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid end date '{end}'. Expected YYYY-MM-DD."
            )

    # Build base query joining Customer (left join) and counting SaleItems
    item_count_subq = (
        db.query(SaleItem.sale_id, func.count(SaleItem.id).label("item_count"))
        .group_by(SaleItem.sale_id)
        .subquery()
    )

    query = (
        db.query(
            Sale,
            Customer.name.label("customer_name"),
            func.coalesce(item_count_subq.c.item_count, 0).label("item_count"),
        )
        .outerjoin(Customer, Sale.customer_id == Customer.id)
        .outerjoin(item_count_subq, Sale.id == item_count_subq.c.sale_id)
    )

    # Date range filter
    if start_dt is not None:
        query = query.filter(Sale.created_at >= start_dt)
    if end_dt is not None:
        query = query.filter(Sale.created_at <= end_dt)

    # Search filter: customer name OR product name in any SaleItem
    if search is not None:
        search_pattern = f"%{search}%"
        product_match = (
            db.query(SaleItem.sale_id)
            .filter(SaleItem.product_name.ilike(search_pattern))
            .subquery()
        )
        from sqlalchemy import or_, exists
        query = query.filter(
            or_(
                Customer.name.ilike(search_pattern),
                Sale.id.in_(db.query(product_match.c.sale_id)),
            )
        )

    rows = query.order_by(Sale.created_at.desc()).all()

    result = []
    for sale, customer_name, item_count in rows:
        result.append(
            SaleSummaryOut(
                id=sale.id,
                created_at=sale.created_at,
                customer_name=customer_name,
                total=sale.total,
                payment_status=sale.payment_status,
                item_count=item_count,
            )
        )
    return result


@router.get("/{sale_id}", response_model=ReceiptOut)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")

    customer = db.get(Customer, sale.customer_id) if sale.customer_id else None
    items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()

    return ReceiptOut(
        sale_id=sale.id,
        created_at=sale.created_at,
        customer_name=customer.name if customer else None,
        items=[
            ReceiptItem(
                product_name=i.product_name,
                qty=i.qty,
                unit_price=i.unit_price,
                line_total=i.line_total,
            )
            for i in items
        ],
        subtotal=sale.subtotal,
        discount_pct=sale.discount_pct,
        discount_amount=sale.discount_amount,
        total=sale.total,
        payment_status=sale.payment_status,
    )
