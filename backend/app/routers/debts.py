"""Debts router: list unpaid sales and mark them paid."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Customer, Sale, SaleItem
from app.schemas import SaleSummaryOut
from app.security import require_roles

router = APIRouter(prefix="/debts", tags=["debts"])

_allowed = require_roles("admin", "manager", "salesman")


def _build_summary(db: Session, sale: Sale) -> SaleSummaryOut:
    customer_name = None
    if sale.customer_id is not None:
        cust = db.get(Customer, sale.customer_id)
        customer_name = cust.name if cust else None

    item_count = (
        db.query(func.count(SaleItem.id))
        .filter(SaleItem.sale_id == sale.id)
        .scalar()
        or 0
    )

    return SaleSummaryOut(
        id=sale.id,
        created_at=sale.created_at,
        customer_name=customer_name,
        total=sale.total,
        payment_status=sale.payment_status,
        item_count=item_count,
    )


@router.get("", response_model=list[SaleSummaryOut])
def list_debts(
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    """Return all unpaid sales ordered by created_at DESC."""
    sales = (
        db.query(Sale)
        .filter(Sale.payment_status == "Unpaid")
        .order_by(Sale.created_at.desc())
        .all()
    )
    return [_build_summary(db, s) for s in sales]


@router.post("/{sale_id}/pay", response_model=SaleSummaryOut)
def mark_paid(
    sale_id: int,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    """Mark a sale as paid. Idempotent — already-paid sales are returned unchanged."""
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.payment_status != "Paid":
        sale.payment_status = "Paid"
        db.commit()
        db.refresh(sale)

    return _build_summary(db, sale)
