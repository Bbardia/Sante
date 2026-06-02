"""Checkout service: the financial + inventory core of the POS.

`perform_checkout` validates a cart, checks stock across the whole cart,
deducts inventory transactionally (rolling back on any failure), persists a
normalized Sale (header + line items) and returns a ReceiptOut.
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Customer, Inventory, Product, Recipe, Sale, SaleItem
from app.schemas import CheckoutRequest, ReceiptItem, ReceiptOut


def perform_checkout(db: Session, req: CheckoutRequest) -> ReceiptOut:
    # 1. Empty cart guard
    if not req.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # 2. Pay-later requires a customer
    if req.pay_later and req.customer_id is None:
        raise HTTPException(
            status_code=400,
            detail="A customer is required for a pay-later (debt) sale",
        )

    # 3. Resolve customer
    customer = None
    if req.customer_id is not None:
        customer = db.get(Customer, req.customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

    # 4. Build line items (validate products + quantities)
    lines: list[tuple[Product, float, float]] = []
    for item in req.items:
        p = db.get(Product, item.product_id)
        if p is None:
            raise HTTPException(
                status_code=404, detail=f"Product {item.product_id} not found"
            )
        if item.qty <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Quantity for product {item.product_id} must be greater than 0",
            )
        line_total = p.price * item.qty
        lines.append((p, item.qty, line_total))

    # 5. Money math
    subtotal = sum(line_total for (_, _, line_total) in lines)
    discount_pct = req.discount_pct or 0
    if discount_pct < 0 or discount_pct > 100:
        raise HTTPException(
            status_code=400, detail="discount_pct must be between 0 and 100"
        )
    discount_amount = subtotal * discount_pct / 100
    total = subtotal - discount_amount
    payment_status = "Unpaid" if req.pay_later else "Paid"

    # 6. Aggregate ingredient requirements across the whole cart
    required: dict[int, float] = {}
    for product, qty, _ in lines:
        recipes = db.query(Recipe).filter(Recipe.product_id == product.id).all()
        for r in recipes:
            required[r.ingredient_id] = required.get(r.ingredient_id, 0.0) + r.qty * qty

    # 7. Stock check (before any mutation)
    shortages = []
    for ing_id, need in required.items():
        inv = db.get(Inventory, ing_id)
        if inv is None or inv.qty < need:
            shortages.append(
                {
                    "ingredient": inv.name if inv else str(ing_id),
                    "available": inv.qty if inv else 0,
                    "needed": need,
                }
            )
    if shortages:
        raise HTTPException(
            status_code=400,
            detail={"message": "Insufficient stock", "shortages": shortages},
        )

    try:
        # 8. Deduct inventory (keep avg_price stable by reducing total_value by
        #    consumed * avg — fixes a legacy bug that only reduced qty).
        for ing_id, need in required.items():
            inv = db.get(Inventory, ing_id)
            avg = inv.total_value / inv.qty if inv.qty > 0 else 0
            inv.qty -= need
            inv.total_value = max(0.0, inv.total_value - need * avg)

        # 9. Persist Sale header + line items
        sale = Sale(
            created_at=datetime.now(),
            customer_id=customer.id if customer else None,
            subtotal=subtotal,
            discount_pct=discount_pct,
            discount_amount=discount_amount,
            total=total,
            payment_status=payment_status,
        )
        db.add(sale)
        db.flush()

        for product, qty, line_total in lines:
            db.add(
                SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    product_name=product.name,
                    qty=qty,
                    unit_price=product.price,
                    line_total=line_total,
                )
            )

        # 10. Commit
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ReceiptOut(
        sale_id=sale.id,
        created_at=sale.created_at,
        customer_name=customer.name if customer else None,
        items=[
            ReceiptItem(
                product_name=product.name,
                qty=qty,
                unit_price=product.price,
                line_total=line_total,
            )
            for product, qty, line_total in lines
        ],
        subtotal=subtotal,
        discount_pct=discount_pct,
        discount_amount=discount_amount,
        total=total,
        payment_status=payment_status,
    )
