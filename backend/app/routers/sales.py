from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Customer, Sale, SaleItem
from app.schemas import CheckoutRequest, ReceiptItem, ReceiptOut
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
