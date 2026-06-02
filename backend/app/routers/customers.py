from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Customer
from app.schemas import CustomerCreate, CustomerOut, CustomerUpdate
from app.security import require_roles

router = APIRouter(prefix="/customers", tags=["customers"])

_allowed = require_roles("admin", "manager", "salesman")


@router.get("", response_model=List[CustomerOut])
def list_customers(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    query = db.query(Customer)
    if search:
        query = query.filter(Customer.name.contains(search))
    return query.order_by(Customer.name).all()


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(
    body: CustomerCreate,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    if body.discount < 0:
        raise HTTPException(status_code=400, detail="discount cannot be negative")

    existing = (
        db.query(Customer)
        .filter(func.lower(Customer.name) == body.name.lower())
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Customer name already exists")

    customer = Customer(name=body.name, discount=body.discount)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    if body.name is not None:
        clash = (
            db.query(Customer)
            .filter(
                func.lower(Customer.name) == body.name.lower(),
                Customer.id != customer_id,
            )
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail="Customer name already exists")
        customer.name = body.name

    if body.discount is not None:
        if body.discount < 0:
            raise HTTPException(status_code=400, detail="discount cannot be negative")
        customer.discount = body.discount

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=200)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()
    return {"detail": "Deleted"}
